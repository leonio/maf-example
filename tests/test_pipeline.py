"""End to end, offline: the real agents, tools, workflow and API, with the scripted model.

The interactive test plays the human through the HTTP API exactly as the UI does: answer a question, end the
interview early, reject the spec with a reason, approve the revision. Then it runs the generated app's own tests.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from dataclasses import replace

import httpx
import pytest

from designpipeline import config
from designpipeline.app import create_app
from designpipeline.tools.workspace import RunWorkspace


@pytest.fixture
def settings(tmp_path):
    return replace(config.Settings(), output_root=tmp_path / "output", mock_delay=0)


@pytest.fixture
async def client(settings):
    app = create_app(settings)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        c.manager = app.state.manager  # type: ignore[attr-defined]
        yield c
        await app.state.manager.shutdown()


async def wait_for(client, run_id: str, predicate, timeout: float = 20) -> dict:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        run = (await client.get(f"/api/runs/{run_id}")).json()
        if predicate(run):
            return run
        await asyncio.sleep(0.02)
    raise AssertionError(f"Timed out; last status {run['status']}, pending {run['pending']}")


def kinds(run: dict) -> list[str]:
    return [e["kind"] for e in run["events"]]


async def test_auto_run_reaches_a_merge_request_after_one_rework_round(client, settings):
    started = (await client.post("/api/runs", json={"idea": "A tiny task tracker", "autoAnswer": True})).json()
    run = await wait_for(client, started["id"], lambda r: r["status"] not in ("running", "waiting"))

    assert run["status"] == "done", run["error"]
    reviews = [e["review"] for e in run["events"] if e["kind"] == "review"]
    assert [r["report"]["verdict"] for r in reviews] == ["ChangesRequested", "Approved"]
    assert [r["next"] for r in reviews] == ["Rework", "Ship"]

    tools = [(e["agent"], e["tool"]) for e in run["events"] if e["kind"] == "tool"]
    assert ("tester", "write_test_file") in tools
    # The release agent asks for all four in one reply, so they run in parallel and finish in any order.
    assert sorted(t for a, t in tools if a == "merge-request") == [
        "confluence_update_page", "create_pull_request", "jira_add_comment", "jira_transition_issue",
    ]  # fmt: skip

    result = next(e["plan"] for e in run["events"] if e["kind"] == "result")
    assert result["pullRequestUrl"] == "https://github.com/your-org/your-repo/pull/42"
    assert "<h2>" in result["bodyHtml"]
    assert set(run["files"]) == {"README.md", "main.py", "tasks.py", "tests/test_tasks.py"}

    artifacts = (await client.get(f"/api/runs/{run['id']}/artifacts")).json()
    assert {"SPEC.md", "REVIEW-1.md", "REVIEW-2.md", "MERGE_REQUEST.md", "decisions.jsonl", "workflow.mmd"} <= set(
        artifacts
    )

    # The generated app really works: its own tests pass once the rework round has fixed the bug.
    app_root = settings.output_root / run["id"] / "app"
    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=app_root, capture_output=True, text=True
    )
    assert tests.returncode == 0, tests.stderr
    assert "Ran 5 tests" in tests.stderr


async def test_a_human_answers_ends_early_rejects_then_approves(client):
    started = (
        await client.post("/api/runs", json={"idea": "Ein Aufgabentracker", "language": "de", "maxQuestions": 3})
    ).json()
    run_id = started["id"]

    run = await wait_for(client, run_id, lambda r: r["pending"] is not None)
    question = run["pending"]
    assert question["kind"] == "question"
    assert question["question"]["question"] == "Wer wird das im Alltag benutzen?"
    assert (
        await client.post(f"/api/runs/{run_id}/answer", json={"requestId": question["requestId"], "text": "Mein Team"})
    ).status_code == 200
    # The same request cannot be answered twice.
    again = await client.post(f"/api/runs/{run_id}/answer", json={"requestId": question["requestId"], "text": "x"})
    assert again.status_code == 409

    run = await wait_for(client, run_id, lambda r: r["pending"] and r["pending"]["requestId"] != question["requestId"])
    second = run["pending"]
    assert second["question"]["number"] == 2
    await client.post(f"/api/runs/{run_id}/answer", json={"requestId": second["requestId"], "endInterview": True})

    run = await wait_for(client, run_id, lambda r: r["pending"] and r["pending"]["kind"] == "approval")
    approval = run["pending"]
    assert approval["spec"]["title"] == "Team-Aufgabenliste (CLI)"
    no_reason = await client.post(
        f"/api/runs/{run_id}/decision", json={"requestId": approval["requestId"], "approved": False}
    )
    assert no_reason.status_code == 422
    await client.post(
        f"/api/runs/{run_id}/decision",
        json={"requestId": approval["requestId"], "approved": False, "reason": "Fälligkeiten fehlen"},
    )

    run = await wait_for(client, run_id, lambda r: r["pending"] and r["pending"]["requestId"] != approval["requestId"])
    revised = run["pending"]
    assert revised["kind"] == "approval"
    assert any("Fälligkeiten fehlen" in a for a in revised["spec"]["assumptions"])
    await client.post(f"/api/runs/{run_id}/decision", json={"requestId": revised["requestId"], "approved": True})

    run = await wait_for(client, run_id, lambda r: r["status"] not in ("running", "waiting"))
    assert run["status"] == "done", run["error"]
    assert kinds(run).count("question") == 2
    assert kinds(run).count("approval") == 2

    decisions = [
        json.loads(line)
        for line in (await client.get(f"/api/runs/{run_id}/artifacts/decisions.jsonl")).text.splitlines()
    ]
    assert [d["decision"]["approved"] for d in decisions] == [False, True]
    assert decisions[0]["decision"]["reason"] == "Fälligkeiten fehlen"
    assert (await client.get(f"/api/runs/{run_id}/artifacts/SPEC.md")).text.startswith("# Team-Aufgabenliste (CLI)")


async def test_runs_are_listed_again_after_a_restart(client, settings):
    started = (await client.post("/api/runs", json={"idea": "Something", "autoAnswer": True})).json()
    await wait_for(client, started["id"], lambda r: r["status"] == "done")

    app = create_app(settings)  # a fresh process, as far as the run list is concerned
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as fresh:
        runs = (await fresh.get("/api/runs")).json()
        assert [r["id"] for r in runs] == [started["id"]]
        assert (await fresh.get(f"/api/runs/{started['id']}")).json()["events"][-1]["status"] == "done"


async def test_the_stream_replays_from_the_last_event_seen(client):
    started = (await client.post("/api/runs", json={"idea": "Something", "autoAnswer": True})).json()
    run = await wait_for(client, started["id"], lambda r: r["status"] == "done")
    response = await client.get(f"/api/runs/{run['id']}/stream", params={"after": len(run["events"]) - 2})
    ids = [int(line[4:]) for line in response.text.splitlines() if line.startswith("id: ")]
    assert ids == [len(run["events"]) - 1, len(run["events"])]
    assert "event: end" in response.text


def test_the_workspace_refuses_paths_outside_the_app(tmp_path):
    ws = RunWorkspace(tmp_path / "run")
    with pytest.raises(PermissionError):
        ws.resolve_in_app("../secrets.txt")
    with pytest.raises(PermissionError):
        ws.resolve_in_app("main.py", required_prefix="tests")
    assert ws.resolve_in_app("tests/test_x.py", required_prefix="tests").name == "test_x.py"
