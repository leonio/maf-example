"""The web app: a small JSON API, a server-sent-event stream per run, and the built SvelteKit UI.

Run it with `uv run design-pipeline` (http://127.0.0.1:8000). During UI development run `pnpm dev` in `web/`
as well; Vite proxies `/api` here (see web/vite.config.ts).

Reading order: this file -> workflow/runs.py -> workflow/pipeline.py -> workflow/executors.py -> agents.py ->
tools/* -> rag.py -> llm/scripted.py.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from . import config
from .contracts import InterviewAnswer, SpecApprovalDecision
from .render import to_html
from .workflow.runs import RequestMismatch, Run, RunManager, RunOptions

log = logging.getLogger("designpipeline")
UI_BUILD = config.ROOT / "web" / "build"
ARTIFACTS = ("SPEC.md", "REVIEW-1.md", "REVIEW-2.md", "REVIEW-3.md", "REVIEW-4.md", "REVIEW-5.md",
             "MERGE_REQUEST.md", "decisions.jsonl", "workflow.mmd")  # fmt: skip


class StartRun(BaseModel):
    idea: str = Field(min_length=3, max_length=2000)
    work_item_key: str = Field(default="", alias="workItemKey", max_length=40, pattern=r"^[A-Za-z0-9_-]*$")
    max_questions: int | None = Field(default=None, alias="maxQuestions", ge=1, le=20)
    max_review_rounds: int | None = Field(default=None, alias="maxReviewRounds", ge=1, le=5)
    language: Literal["en", "de"] = "en"
    auto_answer: bool = Field(default=False, alias="autoAnswer")


class Answer(BaseModel):
    request_id: str = Field(alias="requestId")
    text: str = Field(default="", max_length=4000)
    end_interview: bool = Field(default=False, alias="endInterview")


class Decision(BaseModel):
    request_id: str = Field(alias="requestId")
    approved: bool
    reason: str | None = Field(default=None, max_length=4000)


def create_app(settings: config.Settings | None = None) -> FastAPI:
    settings = settings or config.load()
    manager = RunManager(settings, config.ROOT)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await manager.shutdown()

    app = FastAPI(title="Design pipeline", lifespan=lifespan)
    app.state.manager = manager

    def find(run_id: str) -> Run:
        run = manager.get(run_id)
        if run is None:
            raise HTTPException(404, "No such run.")
        return run

    @app.get("/api/config")
    def get_config() -> dict:
        return {
            "provider": settings.provider,
            "model": None if settings.is_mock else settings.model,
            "models": settings.models,
            "defaults": {
                "maxQuestions": settings.max_questions,
                "maxReviewRounds": settings.max_review_rounds,
                "workItemKey": settings.work_item_key,
            },
            "limits": {k: list(v) for k, v in config.LIMITS.items()},
            "integrations": {
                "jira": "mock" if settings.jira.use_mock else settings.jira.base_url,
                "confluence": "mock" if settings.confluence.use_mock else settings.confluence.base_url,
                "github": "mcp" if settings.github_mcp and settings.github_token else "mock",
            },
        }

    @app.get("/api/runs")
    def list_runs() -> list[dict]:
        return [r.meta() for r in manager.list()]

    @app.post("/api/runs", status_code=201)
    async def start_run(body: StartRun) -> dict:
        try:
            run = manager.start(RunOptions(
                idea=body.idea.strip(),
                work_item_key=body.work_item_key.strip().upper() or settings.work_item_key,
                max_questions=body.max_questions or settings.max_questions,
                max_review_rounds=body.max_review_rounds or settings.max_review_rounds,
                language=body.language,
                auto_answer=body.auto_answer,
            ))  # fmt: skip
        except ValueError as e:  # e.g. a provider without a key
            raise HTTPException(400, str(e)) from e
        return run.meta()

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        run = find(run_id)
        return {**run.meta(), "pending": run.pending, "events": run.events, "files": run.workspace.list_app_files()}

    @app.get("/api/runs/{run_id}/stream")
    async def stream(run_id: str, request: Request, after: int = 0) -> StreamingResponse:
        run = find(run_id)
        # EventSource sends Last-Event-ID when it reconnects; prefer it to the query string.
        last = request.headers.get("last-event-id")
        after = int(last) if last and last.isdigit() else after

        async def events():
            async for event in run.follow(after):
                if await request.is_disconnected():
                    break
                if event["kind"] == "ping":
                    yield ": ping\n\n"
                else:
                    yield f"id: {event['seq']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "event: end\ndata: {}\n\n"

        headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        return StreamingResponse(events(), media_type="text/event-stream", headers=headers)

    @app.post("/api/runs/{run_id}/answer")
    def answer(run_id: str, body: Answer) -> dict:
        if not body.text.strip() and not body.end_interview:
            raise HTTPException(422, "An answer needs some text.")
        respond(
            find(run_id), body.request_id, InterviewAnswer(text=body.text.strip(), end_interview=body.end_interview)
        )
        return {"ok": True}

    @app.post("/api/runs/{run_id}/decision")
    def decide(run_id: str, body: Decision) -> dict:
        reason = (body.reason or "").strip() or None
        if not body.approved and not reason:
            raise HTTPException(422, "Say what is wrong or missing, so the interviewer can fix it.")
        respond(
            find(run_id), body.request_id, SpecApprovalDecision(approved=body.approved, reason=reason, decided_by="web")
        )
        return {"ok": True}

    def respond(run: Run, request_id: str, response) -> None:
        try:
            run.respond(request_id, response)
        except RequestMismatch as e:
            raise HTTPException(409, str(e)) from e

    @app.post("/api/runs/{run_id}/cancel")
    def cancel(run_id: str) -> dict:
        manager.cancel(find(run_id))
        return {"ok": True}

    @app.get("/api/runs/{run_id}/files/{path:path}")
    def read_file(run_id: str, path: str) -> dict:
        run = find(run_id)
        try:
            full = run.workspace.resolve_in_app(path)
        except PermissionError as e:
            raise HTTPException(400, str(e)) from e
        if not full.is_file():
            raise HTTPException(404, "No such file.")
        content = full.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content, "html": to_html(content) if path.lower().endswith(".md") else None}

    @app.get("/api/runs/{run_id}/artifacts")
    def list_artifacts(run_id: str) -> list[str]:
        run = find(run_id)
        return [name for name in ARTIFACTS if (run.workspace.root / name).is_file()]

    @app.get("/api/runs/{run_id}/artifacts/{name}")
    def read_artifact(run_id: str, name: str) -> PlainTextResponse:
        if name not in ARTIFACTS:
            raise HTTPException(404, "No such artefact.")
        content = find(run_id).workspace.read_artifact(name)
        if content is None:
            raise HTTPException(404, "Not written yet.")
        return PlainTextResponse(content, media_type="text/markdown; charset=utf-8" if name.endswith(".md") else None)

    @app.get("/api/runs/{run_id}/download")
    def download(run_id: str) -> Response:
        """The generated app plus SPEC.md / REVIEW-n.md / MERGE_REQUEST.md, as a zip."""
        run = find(run_id)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel in run.workspace.list_app_files():
                zf.write(run.workspace.app_root / rel, f"app/{rel}")
            for name in ARTIFACTS:
                if (run.workspace.root / name).is_file():
                    zf.write(run.workspace.root / name, name)
        headers = {"Content-Disposition": f'attachment; filename="{run.id}.zip"'}
        return Response(buffer.getvalue(), media_type="application/zip", headers=headers)

    # --- the UI -----------------------------------------------------------------------------------------------
    # The SvelteKit app is built to static files (adapter-static, SPA fallback). Any path that is not an API
    # route or a real file gets index.html, and the client-side router takes it from there.
    @app.get("/{path:path}", include_in_schema=False)
    def ui(path: str) -> Response:
        if path.startswith("api/"):
            raise HTTPException(404)
        if not UI_BUILD.is_dir():
            return PlainTextResponse(
                "The UI is not built yet. Run `pnpm install && pnpm build` in web/ (or use `pnpm dev` there and open "
                "http://localhost:5173).",
                status_code=503,
            )
        candidate = (UI_BUILD / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(UI_BUILD.resolve()):
            return FileResponse(candidate)
        return FileResponse(UI_BUILD / "index.html")

    return app


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = config.load()
    mode = "offline, scripted model" if settings.is_mock else f"{settings.provider} / {settings.model}"
    log.info("Design pipeline on http://%s:%s (%s)", settings.host, settings.port, mode)
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="warning")


if __name__ == "__main__":
    main()
