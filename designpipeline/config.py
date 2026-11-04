"""Settings, read once from the environment (and a `.env` file next to `pyproject.toml`, if there is one).

Every knob comes from a `PIPELINE_*` environment variable; `.env.example` lists each one with its default. Secrets (API keys, tokens) only ever come from the environment, never from a file in git.

Per-run choices (the question budget, review rounds, work item key, auto-answer and the language) are made in the
UI when a run is started; the values here are the defaults the form starts from and the limits it enforces.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent  # the project folder: prompts/, skills/, instructions/, web/
load_dotenv(ROOT / ".env")

Provider = Literal["mock", "openai", "azure-openai", "openai-compatible"]

# The four agents. They match the `agent:` front matter in prompts/ and the mock scripts.
INTERVIEWER, DEVELOPER, TESTER, MERGE_REQUEST = "interviewer", "developer", "tester", "merge-request"
AGENTS = (INTERVIEWER, DEVELOPER, TESTER, MERGE_REQUEST)

LIMITS = {"max_questions": (1, 20), "max_review_rounds": (1, 5)}


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(f"PIPELINE_{name}")
    return value if value not in (None, "") else default


def _bool(name: str, default: bool) -> bool:
    value = _env(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = int(_env(name, str(default)) or default)
    low, high = LIMITS.get(name.lower(), (None, None))
    if low is not None and not low <= value <= high:
        raise ValueError(f"PIPELINE_{name} must be between {low} and {high}, got {value}.")
    return value


@dataclass(frozen=True)
class Atlassian:
    base_url: str
    email: str
    api_token: str | None
    # When true an in-process fake answers instead of Atlassian (httpx.MockTransport). The client code is the same
    # either way, which is the point: only the transport is swapped.
    use_mock: bool


@dataclass(frozen=True)
class Settings:
    provider: Provider = "mock"
    model: str = "gpt-4.1-mini"
    # Per-agent model overrides: PIPELINE_MODEL_DEVELOPER=gpt-4.1. A cheap model is fine for interviewing and
    # paperwork; the developer is where a stronger model pays for itself.
    models: dict[str, str] = field(default_factory=dict)
    api_key: str | None = None
    endpoint: str | None = None

    max_questions: int = 6
    max_review_rounds: int = 2
    work_item_key: str = "DEMO-123"
    output_root: Path = ROOT / "output"
    mock_delay: float = 0.35  # seconds the scripted model "thinks"; keeps the timeline readable. Tests set 0.

    jira: Atlassian = field(default_factory=lambda: Atlassian("https://your-org.atlassian.net", "", None, True))
    confluence: Atlassian = field(default_factory=lambda: Atlassian("https://your-org.atlassian.net", "", None, True))
    confluence_page_id: str = "123456"

    github_owner: str = "your-org"
    github_repo: str = "your-repo"
    # The real GitHub MCP server is used only when this is on *and* a token is set; otherwise a local tool with the
    # same name and parameters stands in (tools/github.py).
    github_mcp: bool = False
    github_mcp_url: str = "https://api.githubcopilot.com/mcp/"
    github_token: str | None = None

    host: str = "127.0.0.1"
    port: int = 8000

    def model_for(self, agent: str) -> str:
        return self.models.get(agent, self.model)

    @property
    def is_mock(self) -> bool:
        return self.provider == "mock"

    def endpoint_url(self) -> str | None:
        """The base URL for the OpenAI-compatible client. OpenAI itself needs none (the SDK's default)."""
        if self.endpoint:
            return self.endpoint.rstrip("/") + "/"
        if self.provider == "azure-openai":
            raise ValueError(
                "PIPELINE_ENDPOINT is required for azure-openai, e.g. https://<resource>.openai.azure.com/openai/v1/"
            )
        if self.provider == "openai-compatible":
            raise ValueError("PIPELINE_ENDPOINT is required for openai-compatible, e.g. http://localhost:11434/v1/")
        return None


def load() -> Settings:
    provider = (_env("PROVIDER", "mock") or "mock").lower()
    if provider not in ("mock", "openai", "azure-openai", "openai-compatible"):
        raise ValueError(
            f"PIPELINE_PROVIDER must be mock, openai, azure-openai or openai-compatible, got {provider!r}."
        )
    models = {a: m for a in AGENTS if (m := _env(f"MODEL_{a.upper().replace('-', '_')}"))}

    def atlassian(prefix: str) -> Atlassian:
        return Atlassian(
            base_url=_env(f"{prefix}_BASE_URL", "https://your-org.atlassian.net") or "",
            email=_env(f"{prefix}_EMAIL", "") or "",
            api_token=_env(f"{prefix}_API_TOKEN"),
            use_mock=_bool(f"{prefix}_USE_MOCK", True),
        )

    output = Path(_env("OUTPUT_ROOT", str(ROOT / "output")) or "output")
    return Settings(
        provider=provider,  # type: ignore[arg-type]
        model=_env("MODEL", "gpt-4.1-mini") or "gpt-4.1-mini",
        models=models,
        api_key=_env("API_KEY") or os.environ.get("OPENAI_API_KEY"),
        endpoint=_env("ENDPOINT"),
        max_questions=_int("MAX_QUESTIONS", 6),
        max_review_rounds=_int("MAX_REVIEW_ROUNDS", 2),
        work_item_key=_env("WORK_ITEM_KEY", "DEMO-123") or "DEMO-123",
        output_root=output if output.is_absolute() else ROOT / output,
        mock_delay=float(_env("MOCK_DELAY", "0.35") or 0.35),
        jira=atlassian("JIRA"),
        confluence=atlassian("CONFLUENCE"),
        confluence_page_id=_env("CONFLUENCE_PAGE_ID", "123456") or "123456",
        github_owner=_env("GITHUB_OWNER", "your-org") or "your-org",
        github_repo=_env("GITHUB_REPO", "your-repo") or "your-repo",
        github_mcp=_bool("GITHUB_MCP", False),
        github_mcp_url=_env("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/") or "",
        github_token=_env("GITHUB_TOKEN"),
        host=_env("HOST", "127.0.0.1") or "127.0.0.1",
        port=int(_env("PORT", "8000") or 8000),
    )
