"""Every shape that crosses a boundary: what each agent must hand back, and what flows along the workflow's edges.

Two families, kept apart on purpose:

* **Agent outputs** are "what the model said". Each agent answers with JSON that Agent Framework parses into one
  of these models (`agent.run(..., options={"response_format": Model})` then `response.value`). The JSON schema
  sent to the model is generated from these classes, so the `Field(description=...)` texts double as prompt text.
* **Workflow messages** are "what the next step needs". Sometimes the same shape, often enriched by the executor
  (round numbers, routing decisions, file lists read from disk rather than claimed by the model).

All of them serialise with camelCase names: that is what the prompts and the UI use, and Pydantic accepts either
spelling on the way in. Enums are strings ("Approved", not 0), which measurably helps smaller models.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Contract(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


# --- Agent outputs ----------------------------------------------------------------------------------------------


class RequirementsSpec(Contract):
    """The contract between "what we want" and "what gets built"."""

    title: str = Field(description="Short product name, e.g. 'Team Task Tracker CLI'.")
    summary: str = Field(description="Two or three sentences describing the app.")
    primary_user: str = Field(description="Who uses it.")
    app_kind: str = Field(description="'cli' or 'web-api'.")
    user_stories: list[str] = Field(description="User stories in 'As a ..., I want ..., so that ...' form.")
    acceptance_criteria: list[str] = Field(description="Testable acceptance criteria, Given/When/Then preferred.")
    assumptions: list[str] = Field(description="Assumptions made where the stakeholder did not decide.")
    out_of_scope: list[str] = Field(description="Things explicitly not being built now.")


class InterviewTurn(Contract):
    """One turn of the requirements interview."""

    done: bool = Field(description="True only when the interview is finished and `spec` is filled in.")
    question: str | None = Field(
        default=None, description="The single next question for the stakeholder. Null when done."
    )
    why: str | None = Field(default=None, description="One sentence telling the stakeholder why this question matters.")
    suggested_answers: list[str] | None = Field(
        default=None, description="Two to four short suggested answers. The stakeholder may also type their own."
    )
    spec: RequirementsSpec | None = Field(
        default=None, description="The finished specification. Only when done is true."
    )


class DeveloperReport(Contract):
    """What the developer agent reports after writing files."""

    summary: str = Field(description="One paragraph describing what was implemented or fixed.")
    files_written: list[str] = Field(description="Relative paths of every file written in this round.")
    assumptions: list[str] = Field(description="Assumptions or shortcuts taken.")


class ReviewVerdict(StrEnum):
    APPROVED = "Approved"
    CHANGES_REQUESTED = "ChangesRequested"


class Severity(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ReviewFinding(Contract):
    severity: Severity
    file: str = Field(description="Relative path of the file the finding is about.")
    message: str = Field(description="What is wrong and what to do instead.")

    @property
    def is_blocking(self) -> bool:
        return self.severity is Severity.HIGH


class TesterReport(Contract):
    """What the tester agent decides."""

    verdict: ReviewVerdict
    summary: str = Field(description="Two or three sentences summarising the review.")
    findings: list[ReviewFinding]
    tests_written: list[str] = Field(description="Relative paths of the test files written.")


class MergeRequestPlan(Contract):
    """What the release agent hands back once the paperwork is done."""

    branch: str = Field(description="Branch name following the git-workflow skill.")
    title: str
    body: str = Field(description="Markdown body for the merge request.")
    commands: list[str] = Field(
        description="Exact shell commands, in order, to commit and push the work and open the MR."
    )
    pull_request_url: str | None = Field(
        default=None, description="URL of the created (or mocked) pull request, if any."
    )
    notes: list[str] = Field(description="Anything that went wrong or needs a human.")


# --- Workflow messages ------------------------------------------------------------------------------------------


class DesignBrief(Contract):
    """Start message: the raw product idea typed by the user."""

    idea: str
    work_item_key: str


class InterviewQuestion(Contract):
    """A question for the stakeholder. The interviewer raises it with `ctx.request_info`; the host answers it."""

    number: int
    budget: int
    question: str
    why: str
    suggested_answers: list[str]


class InterviewAnswer(Contract):
    """The human's reply. `end_interview` (the UI's "that's enough" button, or typing /done) forces a spec."""

    text: str
    end_interview: bool = False

    @property
    def ends_interview(self) -> bool:
        return self.end_interview or self.text.strip() in ("/done", "/d")


class SpecApprovalRequest(Contract):
    """A human gate before any code is written."""

    spec: RequirementsSpec
    markdown: str


class SpecApprovalDecision(Contract):
    """The human's decision. The reason is mandatory for rejections and optional for approvals; either way it is
    written to `decisions.jsonl` next to the AI output, so the "why" behind every human call stays with the work."""

    approved: bool
    reason: str | None = None
    decided_by: str = "stakeholder"


class ApprovedSpec(Contract):
    """Interviewer -> Developer once the human has approved the spec."""

    spec: RequirementsSpec


class ImplementationRound(Contract):
    """Developer -> Tester."""

    round: int
    report: DeveloperReport
    files_on_disk: list[str]


class NextStep(StrEnum):
    REWORK = "Rework"
    SHIP = "Ship"


class ReviewOutcome(Contract):
    """Tester -> Developer (Rework) or Tester -> Release (Ship). Edges route on `next` only."""

    round: int
    report: TesterReport
    next: NextStep


class StageUpdate(Contract):
    """Progress for the host, yielded by executors with `ctx.yield_output`.

    `code` and `params` are language-neutral (the UI translates them: `develop.started` + `{round: 2}` becomes
    "Rework round 2: fixing review findings..." or "Nacharbeit, Runde 2: ..."). `detail` carries free text from a
    model, shown as it is. In Agent Framework for Python, custom data reaches the host through `yield_output`;
    the host tells progress from results by type.
    """

    stage: str
    code: str
    params: dict[str, Any] = Field(default_factory=dict)
    detail: str | None = None
