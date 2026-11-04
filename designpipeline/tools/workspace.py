"""The folder one run writes into, and the sandboxed file tools the developer and tester agents get.

```
output/20261104-104512-team-task-tracker/
  app/               <- the generated application (developer + tester write here)
  SPEC.md            <- approved specification
  REVIEW-1.md ...    <- one per review round
  MERGE_REQUEST.md   <- final instructions
  decisions.jsonl    <- every human decision, with its reason
  workflow.mmd       <- Mermaid diagram of the workflow graph
  run.json           <- the run's settings and status (for the runs list)
  events.jsonl       <- everything the UI showed, replayed when you reopen the run
```

Keeping the AI's artefacts and the human's decisions side by side in one folder means you can always answer "why
does the app look like this?" by reading the run folder top to bottom.

**How a Python function becomes a tool.** `tool(name=..., description=...)` wraps a function; its parameters (and
their `Annotated[..., Field(description=...)]`) become the JSON schema the model sees. When the model returns a
function call, the chat client's function-invocation layer runs it and sends the result back: we never write a
tool-call loop ourselves.

**Least privilege per agent.** The tester gets `write_test_file`, which can only write under `tests/`. It cannot
"fix" production code to make its own review pass; that separation of duties is enforced in code, not just asked
for in the prompt. Prompts are requests; tool boundaries are guarantees.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated

from agent_framework import FunctionTool, tool
from pydantic import Field

MAX_FILE_CHARS = 64 * 1024
IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".venv", "node_modules", ".git"}


class RunWorkspace:
    def __init__(self, root: Path):
        self.root = root
        self.app_root = root / "app"
        self.app_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(cls, output_root: Path, idea: str) -> RunWorkspace:
        slug = "-".join(re.sub(r"[^a-z0-9]+", " ", idea.lower()).split()[:5]) or "run"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        root, n = output_root / f"{stamp}-{slug}", 1
        while root.exists():  # two runs in the same second
            n += 1
            root = output_root / f"{stamp}-{slug}-{n}"
        return cls(root)

    @property
    def id(self) -> str:
        return self.root.name

    def write_artifact(self, name: str, content: str) -> None:
        (self.root / name).write_text(content, encoding="utf-8")

    def read_artifact(self, name: str) -> str | None:
        path = self.root / name
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def record_decision(self, stage: str, decision: dict) -> None:
        line = json.dumps({"at": datetime.now().astimezone().isoformat(), "stage": stage, "decision": decision})
        with (self.root / "decisions.jsonl").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def list_app_files(self) -> list[str]:
        """Files currently in the app folder, relative, with forward slashes."""
        return sorted(
            p.relative_to(self.app_root).as_posix()
            for p in self.app_root.rglob("*")
            if p.is_file() and not IGNORED_DIRS.intersection(p.relative_to(self.app_root).parts)
        )

    def resolve_in_app(self, relative: str, required_prefix: str | None = None) -> Path:
        """Resolve a model-supplied path inside `app/`, refusing anything that escapes it.

        Never trust a path from a model: a prompt-injected or simply confused one will happily ask for
        `../../.ssh/id_rsa`. Resolve to an absolute path and check containment; looking for ".." in the string is
        not enough (absolute paths, symlinks, odd separators).
        """
        allowed = (self.app_root / (required_prefix or "")).resolve()
        full = (self.app_root / relative).resolve()
        if full != allowed and not full.is_relative_to(allowed):
            raise PermissionError(f"Path '{relative}' is outside the allowed folder '{required_prefix or '.'}'.")
        return full


Path_ = Annotated[str, Field(description="Relative path inside the app workspace, e.g. 'src/main.py'.")]
Content_ = Annotated[str, Field(description="Full file content.")]


class WorkspaceTools:
    def __init__(self, workspace: RunWorkspace):
        self.workspace = workspace

    def _write(self, path: str, content: str, required_prefix: str | None) -> str:
        # Returning an error *string* (instead of raising) lets the model read the problem and correct itself on the
        # next step; a crafted message is more useful to it than a stack trace.
        if len(content) > MAX_FILE_CHARS:
            return f"ERROR: file too large ({len(content)} chars, limit {MAX_FILE_CHARS}). Split it up."
        try:
            full = self.workspace.resolve_in_app(path, required_prefix)
        except PermissionError as e:
            return f"ERROR: {e}"
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8", newline="\n")
        return f"OK: wrote {len(content)} chars to {path}"

    def _tools(self, *, tests_only: bool) -> list[FunctionTool]:
        ws = self.workspace

        @tool(name="list_files", description="List every file in the app workspace, as relative paths.")
        def list_files() -> list[str]:
            return ws.list_app_files()

        @tool(name="read_file", description="Read a text file from the app workspace.")
        def read_file(path: Path_) -> str:
            try:
                full = ws.resolve_in_app(path)
            except PermissionError as e:
                return f"ERROR: {e}"
            if not full.is_file():
                return f"ERROR: '{path}' does not exist. Call list_files to see what is there."
            return full.read_text(encoding="utf-8")

        @tool(name="write_file", description="Create or overwrite a text file in the app workspace.")
        def write_file(path: Path_, content: Content_) -> str:
            return self._write(path, content, None)

        @tool(
            name="write_test_file",
            description="Create or overwrite a test file. Only paths under 'tests/' are allowed.",
        )
        def write_test_file(
            path: Annotated[str, Field(description="Relative path that starts with 'tests/'.")], content: Content_
        ) -> str:
            return self._write(path, content, "tests")

        return [list_files, read_file, write_test_file if tests_only else write_file]

    def developer_tools(self) -> list[FunctionTool]:
        return self._tools(tests_only=False)

    def tester_tools(self) -> list[FunctionTool]:
        return self._tools(tests_only=True)
