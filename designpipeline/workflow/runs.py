"""Hosts workflow runs for the web app: starts them, turns their events into a timeline, waits for the human, and
fans the timeline out to every browser watching.

**How a paused run works.** `workflow.run(brief, stream=True)` streams events until the graph goes idle. When an
executor called `ctx.request_info(...)`, the stream ends with a `request_info` event and the run state
`IDLE_WITH_PENDING_REQUESTS`; nothing is blocked and nothing is lost. When the human answers (an HTTP POST, maybe
minutes later), `workflow.run(responses={request_id: answer}, stream=True)` resumes it from exactly there.

That is what makes the same workflow usable from a console, a browser (here), Teams,
or a test that answers requests in code. The workflow never knows who answered or how long it took. To survive a
server restart while waiting, add a checkpoint storage to the builder and pass `checkpoint_id` when resuming;
without one, a run that was waiting when the server stopped is shown as "interrupted".

**The timeline.** Everything the UI shows is an event with a sequence number, appended to `events.jsonl` in the run
folder. A browser loads the events so far and then follows the live stream (server-sent events) from the last
number it saw, so reloading the page, opening a second tab or reconnecting after a network blip all just work.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import Settings
from ..contracts import (
    DesignBrief,
    InterviewAnswer,
    InterviewQuestion,
    MergeRequestPlan,
    ReviewOutcome,
    SpecApprovalDecision,
    SpecApprovalRequest,
    StageUpdate,
)
from ..prompts import PromptLibrary
from ..render import to_html
from ..tools.workspace import RunWorkspace
from .pipeline import BuiltPipeline, RunOptions, build_pipeline

log = logging.getLogger(__name__)

ACTIVE = ("running", "waiting")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class RequestMismatch(Exception):
    """The answer is for a request that is not (or no longer) pending."""


@dataclass
class Run:
    workspace: RunWorkspace
    options: RunOptions
    created_at: str = field(default_factory=_now)
    status: str = "running"
    error: str | None = None
    title: str | None = None  # the spec title, once there is one
    verdict: str | None = None
    rounds: int = 0
    pending: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    _answer: asyncio.Future | None = None
    _subscribers: set[asyncio.Queue] = field(default_factory=set)
    _task: asyncio.Task | None = None

    @property
    def id(self) -> str:
        return self.workspace.id

    # --- timeline ---------------------------------------------------------------------------------------------

    def emit(self, kind: str, **data: Any) -> dict[str, Any]:
        event = {"seq": len(self.events) + 1, "at": _now(), "kind": kind, **data}
        self.events.append(event)
        with (self.workspace.root / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        for queue in self._subscribers:
            queue.put_nowait(event)
        return event

    def set_status(self, status: str, error: str | None = None) -> None:
        self.status, self.error = status, error
        self.save()
        self.emit("status", status=status, error=error)

    async def follow(self, after: int) -> AsyncIterator[dict[str, Any]]:
        """Every event after `after`, then live ones until the run stops."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)  # subscribe before reading the backlog so nothing falls in between
        try:
            last = after
            for event in list(self.events):
                if event["seq"] > last:
                    last = event["seq"]
                    yield event
            while self.status in ACTIVE or not queue.empty():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield {"kind": "ping"}  # keeps proxies from closing an idle connection
                    continue
                if event["seq"] > last:
                    last = event["seq"]
                    yield event
        finally:
            self._subscribers.discard(queue)

    # --- persistence --------------------------------------------------------------------------------------------

    def meta(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "createdAt": self.created_at,
            "status": self.status,
            "error": self.error,
            "title": self.title,
            "verdict": self.verdict,
            "rounds": self.rounds,
            "options": {
                "idea": self.options.idea,
                "workItemKey": self.options.work_item_key,
                "maxQuestions": self.options.max_questions,
                "maxReviewRounds": self.options.max_review_rounds,
                "language": self.options.language,
                "autoAnswer": self.options.auto_answer,
            },
        }

    def save(self) -> None:
        self.workspace.write_artifact("run.json", json.dumps(self.meta(), indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, root: Path) -> Run:
        meta = json.loads((root / "run.json").read_text(encoding="utf-8"))
        o = meta["options"]
        run = cls(
            workspace=RunWorkspace(root),
            options=RunOptions(
                o["idea"], o["workItemKey"], o["maxQuestions"], o["maxReviewRounds"], o["language"], o["autoAnswer"]
            ),
            created_at=meta["createdAt"],
            status=meta["status"],
            error=meta.get("error"),
            title=meta.get("title"),
            verdict=meta.get("verdict"),
            rounds=meta.get("rounds", 0),
        )
        events_file = root / "events.jsonl"
        if events_file.exists():
            run.events = [
                json.loads(line) for line in events_file.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
        if run.status in ACTIVE:
            # The workflow lived in the old process's memory. Checkpointing would let us resume it instead.
            run.status, run.error = "interrupted", "The server stopped while this run was in progress."
            run.save()
        return run

    # --- the human's side ---------------------------------------------------------------------------------------

    def respond(self, request_id: str, response: InterviewAnswer | SpecApprovalDecision) -> None:
        expected = {"question": InterviewAnswer, "approval": SpecApprovalDecision}
        if not self.pending or self.pending["requestId"] != request_id or self._answer is None or self._answer.done():
            raise RequestMismatch("That question has already been answered, or the run has moved on.")
        if not isinstance(response, expected[self.pending["kind"]]):
            raise RequestMismatch(f"This request expects a {self.pending['kind']} response.")
        self._answer.set_result(response)


class RunManager:
    def __init__(self, settings: Settings, library_root: Path):
        self.settings = settings
        self.library_root = library_root
        self.runs: dict[str, Run] = {}
        settings.output_root.mkdir(parents=True, exist_ok=True)
        for run_json in sorted(settings.output_root.glob("*/run.json")):
            try:
                run = Run.load(run_json.parent)
                self.runs[run.id] = run
            except (OSError, KeyError, ValueError) as e:
                log.warning("Skipping %s: %s", run_json.parent.name, e)

    def list(self) -> list[Run]:
        return sorted(self.runs.values(), key=lambda r: r.created_at, reverse=True)

    def get(self, run_id: str) -> Run | None:
        return self.runs.get(run_id)

    def start(self, options: RunOptions) -> Run:
        run = Run(RunWorkspace.create(self.settings.output_root, options.idea), options)
        self.runs[run.id] = run
        run.save()
        run._task = asyncio.create_task(self._drive(run), name=f"run-{run.id}")
        return run

    def cancel(self, run: Run) -> None:
        if run._task and not run._task.done():
            run._task.cancel()

    async def shutdown(self) -> None:
        tasks = [r._task for r in self.runs.values() if r._task and not r._task.done()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    # --- driving one run ----------------------------------------------------------------------------------------

    async def _drive(self, run: Run) -> None:
        async def on_tool_call(agent: str, tool: str, arguments: str, result: str) -> None:
            run.emit("tool", agent=agent, tool=tool, arguments=arguments, result=result)

        pipeline: BuiltPipeline | None = None
        try:
            # Prompts, skills and instructions are re-read for every run: edit a Markdown file, start a new run.
            library = PromptLibrary(self.library_root)
            pipeline = build_pipeline(self.settings, library, run.workspace, run.options, on_tool_call)
            run.workspace.write_artifact("workflow.mmd", pipeline.mermaid)
            run.emit(
                "started", provider=self.settings.provider, model=None if self.settings.is_mock else self.settings.model
            )

            brief = DesignBrief(idea=run.options.idea, work_item_key=run.options.work_item_key)
            stream = pipeline.workflow.run(brief, stream=True)
            plan: MergeRequestPlan | None = None
            while True:
                pending, failure, result = await self._consume(run, stream)
                plan = result or plan
                if failure:
                    run.set_status("failed", failure)
                    return
                if not pending:
                    break
                request_id, request = pending[0]  # this graph only ever has one open request at a time
                response = await self._ask_human(run, request_id, request)
                stream = pipeline.workflow.run(responses={request_id: response}, stream=True)

            if plan is None:
                run.set_status("failed", "The workflow finished without producing a merge request.")
            else:
                run.set_status("done")
        except asyncio.CancelledError:
            run.pending = None
            run.set_status("cancelled")
        except Exception as e:  # top level of a background task: report it, don't lose it
            log.exception("Run %s failed", run.id)
            run.pending = None
            run.set_status("failed", f"{type(e).__name__}: {e}")
        finally:
            if pipeline:
                await pipeline.aclose()

    async def _consume(self, run: Run, stream) -> tuple[list[tuple[str, Any]], str | None, MergeRequestPlan | None]:
        pending: list[tuple[str, Any]] = []
        failure: str | None = None
        plan: MergeRequestPlan | None = None
        async for event in stream:
            match event.type:
                case "output" | "intermediate":
                    plan = self._on_output(run, event.data) or plan
                case "request_info":
                    pending.append((event.request_id, event.data))
                case "executor_failed" | "failed":
                    details = event.details
                    where = f"Step '{event.executor_id}' failed" if event.executor_id else "Workflow failed"
                    failure = f"{where}: {getattr(details, 'message', None) or details}"
                case "warning":
                    log.warning("Run %s: %s", run.id, event.data)
        return pending, failure, plan

    def _on_output(self, run: Run, data: Any) -> MergeRequestPlan | None:
        if isinstance(data, StageUpdate):
            run.emit("stage", **data.dump())
        elif isinstance(data, ReviewOutcome):
            run.rounds, run.verdict = data.round, str(data.report.verdict)
            run.save()
            run.emit("review", review=data.dump())
        elif isinstance(data, MergeRequestPlan):
            run.emit("result", plan={**data.dump(), "bodyHtml": to_html(data.body)})
            return data
        return None

    async def _ask_human(self, run: Run, request_id: str, request: Any) -> InterviewAnswer | SpecApprovalDecision:
        if isinstance(request, InterviewQuestion):
            run.pending = {"requestId": request_id, "kind": "question", "question": request.dump()}
        elif isinstance(request, SpecApprovalRequest):
            run.title = request.spec.title
            run.pending = {"requestId": request_id, "kind": "approval", "spec": request.spec.dump()}
        else:
            raise TypeError(f"No handler for a request of type {type(request).__name__}.")
        run.emit(**run.pending)  # a "question" or "approval" event, with the request id the answer must quote

        if run.options.auto_answer:
            await asyncio.sleep(self.settings.mock_delay)
            response = _auto_answer(request)
        else:
            run._answer = asyncio.get_running_loop().create_future()
            run.set_status("waiting")
            response = await run._answer

        run.pending, run._answer = None, None
        run.emit("answered", requestId=request_id, response=response.dump(), auto=run.options.auto_answer)
        if run.status != "running":
            run.set_status("running")
        return response


def _auto_answer(request: Any) -> InterviewAnswer | SpecApprovalDecision:
    """First suggestion, then approve. For demos and smoke tests."""
    if isinstance(request, InterviewQuestion):
        return InterviewAnswer(text=request.suggested_answers[0] if request.suggested_answers else "/done")
    return SpecApprovalDecision(
        approved=True, reason="Auto-approved (auto-answer was on for this run).", decided_by="auto"
    )
