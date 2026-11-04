"""The four nodes of the graph. Each wraps one agent with the logic around it: budgets, routing, artefacts.

**Why custom executors and not the agents bound directly?** An `Agent` can be dropped into a `WorkflowBuilder` as
is (it then speaks chat messages). We wrap them because every step needs typed inputs and outputs, a budget or a
routing decision enforced in code, and files written to the run folder. Rule of thumb: bind agents directly for
chat-style chains; wrap them when the step has logic or typed contracts.

**How an executor talks.** `@handler` methods receive messages; the first type parameter of `WorkflowContext` is
what the handler may *send* along edges (`ctx.send_message`), the second what it may *yield* to the host
(`ctx.yield_output`). The builder checks edges against these types, so a new message type cannot silently leak to
the wrong node. Reading the signatures below tells you the whole protocol.

**Human in the loop.** `ctx.request_info(request, ResponseType)` pauses the run and hands `request` to the host
as a `request_info` event; the host's answer arrives at the matching `@response_handler` *of the same executor*.
Because a paused run simply returns, a web host can wait minutes (or, with checkpointing, days) for the human.

**State caveat.** Sessions and counters are plain attributes: fine for an in-process run that lives as long as the
server. To survive a restart (or to wait days for a human), enable checkpointing and move them into workflow state
(`ctx.set_state`), serialising each agent session with `session.to_dict()`.
"""

from __future__ import annotations

import json
from typing import Never

from agent_framework import Agent, AgentSession, Executor, WorkflowContext, handler, response_handler

from ..contracts import (
    ApprovedSpec,
    DesignBrief,
    DeveloperReport,
    ImplementationRound,
    InterviewAnswer,
    InterviewQuestion,
    InterviewTurn,
    MergeRequestPlan,
    NextStep,
    RequirementsSpec,
    ReviewOutcome,
    ReviewVerdict,
    SpecApprovalDecision,
    SpecApprovalRequest,
    StageUpdate,
    TesterReport,
)
from ..render import merge_request_markdown, review_markdown, spec_markdown
from ..tools.workspace import RunWorkspace

# Shared workflow state: facts several steps need. The approved spec is the textbook case: the developer, tester and
# release agent all need it, and threading it through every message would make each one carry baggage.
SPEC_KEY, WORK_ITEM_KEY = "approved-spec", "work-item-key"


def _json(model) -> str:
    return json.dumps(model.dump(), indent=2, ensure_ascii=False)


async def _structured(agent: Agent, prompt: str, session: AgentSession, schema):
    """Run the agent and parse its answer into `schema`.

    Agent Framework sends the schema as the response format and parses the reply (`response.value`). If the model
    returns something that does not parse, this raises, the executor fails and the host sees `executor_failed`. A
    production system might retry once with the parse error appended.
    """
    response = await agent.run(prompt, session=session, options={"response_format": schema})
    value = response.value
    if value is None:
        raise ValueError(f"{agent.name} did not return a valid {schema.__name__}: {response.text[:500]}")
    return value


class InterviewerExecutor(Executor):
    """Step 1: the "grill-me" interview. Loops with the human until a spec is approved, then hands it on."""

    def __init__(self, agent: Agent, workspace: RunWorkspace, max_questions: int, lang: str):
        super().__init__(id="interviewer")
        self.agent, self.workspace, self.max_questions, self.lang = agent, workspace, max_questions, lang
        self.session: AgentSession | None = None
        self.asked = 0
        self.draft: RequirementsSpec | None = None

    @handler
    async def on_brief(self, brief: DesignBrief, ctx: WorkflowContext[ApprovedSpec, StageUpdate]) -> None:
        ctx.set_state(WORK_ITEM_KEY, brief.work_item_key)
        await ctx.yield_output(StageUpdate(stage="interview", code="interview.started", params={"idea": brief.idea}))
        await self._ask(f"Product idea from the stakeholder: {brief.idea}\nWork item: {brief.work_item_key}", ctx)

    @response_handler
    async def on_answer(
        self, question: InterviewQuestion, answer: InterviewAnswer, ctx: WorkflowContext[ApprovedSpec, StageUpdate]
    ) -> None:
        # The budget is enforced in code, not just requested in the prompt. Models are good at following
        # instructions and bad at counting; never rely on a prompt for a hard limit.
        if answer.ends_interview:
            message = "The stakeholder asked to stop here."
        elif self.asked >= self.max_questions:
            message = f"Answer: {answer.text}\nThe question budget is used up."
        else:
            await self._ask(f"Answer: {answer.text}", ctx)
            return
        await self._ask(
            f"{message}\nProduce the final specification now (done = true), labelling anything undecided as an assumption.",
            ctx,
        )

    @response_handler
    async def on_decision(
        self,
        request: SpecApprovalRequest,
        decision: SpecApprovalDecision,
        ctx: WorkflowContext[ApprovedSpec, StageUpdate],
    ) -> None:
        # Keep the human's "why" next to the AI's output, whatever they decided.
        self.workspace.record_decision("spec-approval", {**decision.dump(), "spec": request.spec.title})
        if decision.approved:
            self.workspace.write_artifact("SPEC.md", spec_markdown(request.spec, self.lang))
            ctx.set_state(SPEC_KEY, request.spec)
            await ctx.yield_output(StageUpdate(stage="interview", code="interview.approved"))
            await ctx.send_message(ApprovedSpec(spec=request.spec))
            return
        await ctx.yield_output(StageUpdate(stage="interview", code="interview.rejected", detail=decision.reason))
        await self._ask(
            f"The stakeholder rejected the specification. Their reason: {decision.reason or '(none given)'}\n"
            "Either ask one follow-up question or return a revised specification.",
            ctx,
        )

    async def _ask(self, message: str, ctx: WorkflowContext) -> None:
        # One session for the whole interview = the agent remembers every previous question and answer.
        self.session = self.session or self.agent.create_session()
        turn: InterviewTurn = await _structured(self.agent, message, self.session, InterviewTurn)
        if turn.done and turn.spec:
            self.draft = turn.spec
            await ctx.request_info(
                SpecApprovalRequest(spec=turn.spec, markdown=spec_markdown(turn.spec, self.lang)), SpecApprovalDecision
            )
        elif turn.question:
            self.asked += 1
            question = InterviewQuestion(
                number=self.asked,
                budget=self.max_questions,
                question=turn.question,
                why=turn.why or "",
                suggested_answers=turn.suggested_answers or [],
            )
            await ctx.request_info(question, InterviewAnswer)
        else:
            raise ValueError(f"Interviewer returned neither a question nor a spec: {_json(turn)}")


class DeveloperExecutor(Executor):
    """Step 2: the developer writes the app into the run workspace with file tools. Handles both the first build
    (`ApprovedSpec`) and rework (`ReviewOutcome`).

    **Code goes through tools, not through the answer.** The agent can read what exists before editing (essential
    on rework), each write is validated (path sandbox, size limit) and observable, and the final answer stays a
    small summary instead of a 20 KB JSON blob that is likely to be truncated.

    **Ground truth from disk.** The message passed on lists the files that are *actually* in the workspace, not the
    ones the model says it wrote. Trust tools' side effects over models' claims about them.

    One session across rounds: on rework the developer remembers what it built and why, so the fix is a targeted
    edit rather than a rewrite. The trade-off is context growth; for large apps start each round fresh with a summary.
    """

    def __init__(self, agent: Agent, workspace: RunWorkspace):
        super().__init__(id="developer")
        self.agent, self.workspace = agent, workspace
        self.session: AgentSession | None = None

    @handler
    async def on_spec(self, approved: ApprovedSpec, ctx: WorkflowContext[ImplementationRound, StageUpdate]) -> None:
        await self._build(
            1, f"Implement this approved requirements specification:\n```json\n{_json(approved.spec)}\n```", ctx
        )

    @handler
    async def on_review(self, review: ReviewOutcome, ctx: WorkflowContext[ImplementationRound, StageUpdate]) -> None:
        await self._build(
            review.round + 1,
            f"Review report from the Tester (round {review.round}). Fix the findings:\n```json\n{_json(review.report)}\n```",
            ctx,
        )

    async def _build(self, round_: int, prompt: str, ctx: WorkflowContext[ImplementationRound, StageUpdate]) -> None:
        await ctx.yield_output(StageUpdate(stage="develop", code="develop.started", params={"round": round_}))
        self.session = self.session or self.agent.create_session()
        report: DeveloperReport = await _structured(self.agent, prompt, self.session, DeveloperReport)
        files = self.workspace.list_app_files()
        await ctx.yield_output(StageUpdate(
            stage="develop", code="develop.done", params={"round": round_, "files": len(files)}, detail=report.summary
        ))  # fmt: skip
        await ctx.send_message(ImplementationRound(round=round_, report=report, files_on_disk=files))


class TesterExecutor(Executor):
    """Step 3: the tester reviews the code against the spec, writes tests, and the code decides what happens next.

    **The model gives a verdict; code decides the route.** The tester returns a `ReviewVerdict`, but whether we loop
    again is `NextStep`, computed here from the verdict *and* the round budget. The edges then route on `next` only,
    which keeps the policy ("max N rounds, then ship with findings noted") in one testable place instead of hidden
    in an edge lambda or a prompt.

    **Fresh session per round.** Unlike the developer, the tester starts clean every round so it re-checks
    everything against the spec instead of only last round's findings. Independent re-review is the point.
    """

    def __init__(self, agent: Agent, workspace: RunWorkspace, max_rounds: int, lang: str):
        super().__init__(id="tester")
        self.agent, self.workspace, self.max_rounds, self.lang = agent, workspace, max_rounds, lang

    @handler
    async def on_round(
        self, round_: ImplementationRound, ctx: WorkflowContext[ReviewOutcome, StageUpdate | ReviewOutcome]
    ) -> None:
        await ctx.yield_output(StageUpdate(
            stage="test", code="test.started", params={"round": round_.round, "files": len(round_.files_on_disk)}
        ))  # fmt: skip
        spec: RequirementsSpec = ctx.get_state(SPEC_KEY)
        files = "\n".join(f"- {f}" for f in round_.files_on_disk)
        prompt = (
            f"Review round {round_.round} of {self.max_rounds}.\n\n## Specification\n```json\n{_json(spec)}\n```\n\n"
            f"## Developer's summary\n{round_.report.summary}\n\n## Files in the workspace\n{files}"
        )
        report: TesterReport = await _structured(self.agent, prompt, self.agent.create_session(), TesterReport)

        if report.verdict is ReviewVerdict.APPROVED:
            next_step = NextStep.SHIP
        elif round_.round < self.max_rounds:
            next_step = NextStep.REWORK
        else:
            next_step = NextStep.SHIP  # out of rounds: ship anyway, the open findings go in the MR for a human

        outcome = ReviewOutcome(round=round_.round, report=report, next=next_step)
        self.workspace.write_artifact(f"REVIEW-{round_.round}.md", review_markdown(outcome, self.lang))
        await ctx.yield_output(outcome)
        await ctx.yield_output(StageUpdate(
            stage="test", code="test.done", detail=report.summary,
            params={"round": round_.round, "verdict": report.verdict, "findings": len(report.findings), "next": next_step},
        ))  # fmt: skip
        await ctx.send_message(outcome)


UNAPPROVED_NOTE = {
    "en": "Shipped after {n} round(s) WITHOUT tester approval - review the open findings first.",
    "de": "Nach {n} Runde(n) OHNE Freigabe des Testers ausgeliefert - zuerst die offenen Befunde prüfen.",
}


class MergeRequestExecutor(Executor):
    """Step 4: the release agent opens the (mocked) pull request, updates Jira and Confluence through tools, and
    returns the exact git commands for a human. Its result is the workflow's output.

    **Why does an agent do this and not plain code?** Honestly, for a fixed sequence of four API calls, plain code
    is more reliable. It is an agent here to show tool calling against HTTP APIs and MCP, and because the *content*
    (PR body, Jira comment, wiki note) benefits from being written in context. A good hybrid: code makes the calls,
    the model writes the text.
    """

    def __init__(self, agent: Agent, workspace: RunWorkspace, lang: str):
        super().__init__(id="merge-request")
        self.agent, self.workspace, self.lang = agent, workspace, lang

    @handler
    async def on_ship(
        self, outcome: ReviewOutcome, ctx: WorkflowContext[Never, StageUpdate | MergeRequestPlan]
    ) -> None:
        await ctx.yield_output(StageUpdate(stage="release", code="release.started"))
        spec: RequirementsSpec = ctx.get_state(SPEC_KEY)
        files = "\n".join(f"- {f}" for f in self.workspace.list_app_files())
        prompt = (
            f"Work item: {ctx.get_state(WORK_ITEM_KEY)}\n\n## Specification\n```json\n{_json(spec)}\n```\n\n"
            f"## Final review (round {outcome.round})\n```json\n{_json(outcome.report)}\n```\n\n"
            f"## Files\n{files}\n\nThe app lives in the `app/` folder of the run directory."
        )
        plan: MergeRequestPlan = await _structured(self.agent, prompt, self.agent.create_session(), MergeRequestPlan)
        if outcome.report.verdict is not ReviewVerdict.APPROVED:
            # Make the unresolved state impossible to miss, whatever the model wrote.
            plan.notes = [UNAPPROVED_NOTE.get(self.lang, UNAPPROVED_NOTE["en"]).format(n=outcome.round), *plan.notes]
        self.workspace.write_artifact("MERGE_REQUEST.md", merge_request_markdown(plan, self.lang))
        await ctx.yield_output(StageUpdate(stage="release", code="release.done"))
        await ctx.yield_output(plan)
