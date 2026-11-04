"""A chat client that answers from a script instead of a model, so the whole pipeline runs offline.

**Why mock at the chat client?** It is the narrowest seam that still exercises the whole stack: the agent, its
context providers, structured-output parsing, the automatic function-invocation loop (the scripted "model" really
returns function calls and the real tools really run), and the workflow. Only the token generation is fake.

The scripts are a little bit "smart" so an offline run shows every path of the workflow: the interviewer stops
when asked, the developer's first attempt has a bug, the tester spots it by actually reading the file through its
tool, the rework loop fixes it, and the release agent calls all four integration tools. Whatever idea you type, the
mock builds the same small task tracker; switch to a real provider for real behaviour.

Each script decides from the conversation alone (as a model would): the instructions (which language), how many
times the user has written, and the tool calls and results since the last user message.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from agent_framework import BaseChatClient, ChatResponse, ChatResponseUpdate, Content, FunctionInvocationLayer, Message

from ..config import DEVELOPER, INTERVIEWER, MERGE_REQUEST, TESTER
from ..contracts import (
    DeveloperReport,
    InterviewTurn,
    MergeRequestPlan,
    RequirementsSpec,
    ReviewFinding,
    ReviewVerdict,
    Severity,
    TesterReport,
)
from . import generated_app as app
from . import mock_content as text


@dataclass
class Turn:
    instructions: str
    messages: list[Message]
    lang: str = "en"
    user_texts: list[str] = field(default_factory=list)
    results: list[str] = field(default_factory=list)  # tool results since the last user message

    @property
    def last_user(self) -> str:
        return self.user_texts[-1] if self.user_texts else ""

    @property
    def has_tool_results(self) -> bool:
        return bool(self.messages) and self.messages[-1].role == "tool"


def _turn(messages: list[Message], options) -> Turn:
    instructions = "\n".join(
        [str(options.get("instructions") or ""), *(m.text for m in messages if m.role == "system")]
    )
    # The prompts say "write ... in **{{language}}**"; that is how a model would know too.
    turn = Turn(instructions, messages, lang="de" if "**German**" in instructions else "en")
    turn.user_texts = [m.text for m in messages if m.role == "user" and m.text]
    last_user = max((i for i, m in enumerate(messages) if m.role == "user"), default=-1)
    for m in messages[last_user + 1 :]:
        turn.results += [str(c.result) for c in m.contents if c.type == "function_result"]
    return turn


class ScriptedChatClient(FunctionInvocationLayer, BaseChatClient):
    def __init__(self, agent: str, delay: float = 0.35, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
        self.delay = delay

    def _inner_get_response(self, *, messages, options, stream: bool = False, **kwargs):
        script = SCRIPTS.get(self.agent, lambda t: [Content.from_text(f"(mock) No script for agent '{self.agent}'.")])

        async def contents() -> list[Content]:
            if self.delay:
                await asyncio.sleep(self.delay)  # keeps the timeline readable and makes it feel like a model
            return script(_turn(list(messages), options))

        if stream:

            async def updates():
                for item in await contents():
                    yield ChatResponseUpdate(contents=[item], role="assistant")

            return self._build_response_stream(updates())

        async def respond() -> ChatResponse:
            return ChatResponse(messages=[Message("assistant", await contents())])

        return respond()


# --- helpers ----------------------------------------------------------------------------------------------------


def _json(model) -> list[Content]:
    return [Content.from_text(json.dumps(model.dump(), ensure_ascii=False))]


def _calls(*calls: tuple[str, dict]) -> list[Content]:
    # Several calls in one reply = parallel tool calls; the function-invocation layer runs them all.
    return [
        Content.from_function_call(call_id=f"call_{i}_{name}", name=name, arguments=args)
        for i, (name, args) in enumerate(calls)
    ]


# --- Interviewer ------------------------------------------------------------------------------------------------


def interviewer(t: Turn) -> list[Content]:
    questions = text.QUESTIONS[t.lang]
    # Once the interview has ended (budget, "that's enough", or a rejected spec), only specs come back.
    stop = any("Produce the final specification now" in u for u in t.user_texts) or t.last_user.startswith(
        "The stakeholder rejected"
    )
    index = len(t.user_texts) - 1
    if not stop and index < len(questions):
        q, why, options = questions[index]
        return _json(InterviewTurn(done=False, question=q, why=why, suggested_answers=options))

    spec = RequirementsSpec(**text.SPEC[t.lang])
    if t.last_user.startswith("The stakeholder rejected"):
        reason = t.last_user.split("Their reason:", 1)[-1].split("\n", 1)[0].strip()
        spec.assumptions = [*spec.assumptions, text.REVISED[t.lang].format(reason=reason)]
    return _json(InterviewTurn(done=True, spec=spec))


# --- Developer --------------------------------------------------------------------------------------------------


def developer(t: Turn) -> list[Content]:
    fix_round = "Review report" in t.last_user
    if t.has_tool_results:
        summary, assumptions = text.DEVELOPER[t.lang]["fix" if fix_round else "first"]
        files = ["tasks.py", "main.py"] if fix_round else ["main.py", "tasks.py", "README.md"]
        return _json(DeveloperReport(summary=summary, files_written=files, assumptions=assumptions))
    if fix_round:
        return _calls(
            ("read_file", {"path": "tasks.py"}),
            ("write_file", {"path": "tasks.py", "content": app.TASKS_FIXED}),
            ("write_file", {"path": "main.py", "content": app.MAIN_FIXED}),
        )
    return _calls(
        ("list_files", {}),
        ("write_file", {"path": "main.py", "content": app.MAIN}),
        ("write_file", {"path": "tasks.py", "content": app.TASKS}),
        ("write_file", {"path": "README.md", "content": app.README}),
    )


# --- Tester -----------------------------------------------------------------------------------------------------


def tester(t: Turn) -> list[Content]:
    tests = ["tests/test_tasks.py"]
    if not t.has_tool_results:
        return _calls(
            ("list_files", {}),
            ("read_file", {"path": "tasks.py"}),
            ("read_file", {"path": "main.py"}),
            ("write_test_file", {"path": "tests/test_tasks.py", "content": app.TESTS}),
        )
    # The verdict depends on what read_file actually returned - on the code the developer wrote, not on which round
    # we think it is.
    words = text.TESTER[t.lang]
    if any("raise ValueError" in r for r in t.results):
        return _json(TesterReport(
            verdict=ReviewVerdict.APPROVED, summary=words["approved"], tests_written=tests,
            findings=[ReviewFinding(severity=Severity.LOW, file="tasks.py", message=words["low"])],
        ))  # fmt: skip
    return _json(TesterReport(
        verdict=ReviewVerdict.CHANGES_REQUESTED, summary=words["changes"], tests_written=tests,
        findings=[
            ReviewFinding(severity=Severity.HIGH, file="tasks.py", message=words["high"]),
            ReviewFinding(severity=Severity.MEDIUM, file="main.py", message=words["medium"]),
        ],
    ))  # fmt: skip


# --- Merge request ----------------------------------------------------------------------------------------------


def merge_request(t: Turn) -> list[Content]:
    key = m.group(1) if (m := re.search(r"Work item: (\S+)", t.last_user)) else "DEMO-123"
    branch = f"feature/{key}-team-task-tracker"
    words = text.MERGE_REQUEST[t.lang]
    title = words["title"].format(key=key)
    if not t.has_tool_results:
        return _calls(
            (
                "create_pull_request",
                {"head": branch, "base": "main", "title": title, "body": words["pr_body"], "draft": True},
            ),
            ("jira_add_comment", {"issue_key": key, "comment": words["jira"].format(branch=branch)}),
            ("jira_transition_issue", {"issue_key": key, "transition_name": "In Review"}),
            ("confluence_update_page", {"heading": words["wiki_heading"].format(key=key), "content": words["wiki"]}),
        )
    pr_url = next((m.group(1) for r in t.results if (m := re.search(r'"html_url":\s*"([^"]+)"', r))), None)
    return _json(MergeRequestPlan(
        branch=branch, title=title, body=words["body"], pull_request_url=pr_url, notes=[words["note"]],
        commands=[
            "cd app",
            "git init -b main   # skip if this folder is already inside your repo",
            f"git switch -c {branch}",
            "git add main.py tasks.py",
            'git commit -m "feat: scaffold team task tracker CLI"',
            "git add tests/",
            'git commit -m "test: add task tracker tests"',
            "git add README.md",
            'git commit -m "docs: add README"',
            "git remote add origin https://github.com/your-org/your-repo.git   # if needed",
            f"git push -u origin {branch}",
            f'gh pr create --draft --base main --head {branch} --title "{title}" --body-file ../MERGE_REQUEST.md',
        ],
    ))  # fmt: skip


SCRIPTS: dict[str, Callable[[Turn], list[Content]]] = {
    INTERVIEWER: interviewer,
    DEVELOPER: developer,
    TESTER: tester,
    MERGE_REQUEST: merge_request,
}
