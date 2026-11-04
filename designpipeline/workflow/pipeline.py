"""Assembles the four agents and the human gates into one workflow graph.

```
                 ┌── request_info: InterviewQuestion ──▶ host (human answers) ──┐
                 ▼                                                              │
 DesignBrief ─▶ interviewer ◀───────────────────────────────────────────────────┘
                 │  └── request_info: SpecApprovalRequest ──▶ host (approve / reject with reason)
                 │ ApprovedSpec
                 ▼
             developer ◀──────── rework ──────┐
                 │ ImplementationRound        │
                 ▼                            │
               tester ────────────────────────┘
                 │ ship
                 ▼
           merge-request ──▶ MergeRequestPlan (workflow output)
```

(Each run writes the generated Mermaid version to `workflow.mmd`; the UI shows it.)

**Why a hand-built graph instead of the prebuilt orchestrations?** `agent_framework.orchestrations` offers ready-made
patterns: sequential, concurrent (fan out, aggregate), handoff (agents decide who goes next), group chat and
Magentic (a manager agent orchestrates). None of them gives a review loop with a code-enforced round limit *plus*
typed human approval gates, and in an SDLC pipeline the order of steps is policy, not something a model should
improvise. So: `WorkflowBuilder` with explicit edges. Reach for handoff or Magentic when the path genuinely is not
known in advance (support triage, research).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_framework import Workflow, WorkflowBuilder, WorkflowViz

from ..agents import create_agent
from ..config import DEVELOPER, INTERVIEWER, MERGE_REQUEST, TESTER, Settings
from ..contracts import NextStep, ReviewOutcome
from ..prompts import PromptLibrary
from ..tools.github import pull_request_tools
from ..tools.observed import OnCall
from ..tools.tracker import TrackerTools
from ..tools.workspace import RunWorkspace, WorkspaceTools
from .executors import DeveloperExecutor, InterviewerExecutor, MergeRequestExecutor, TesterExecutor


@dataclass
class RunOptions:
    idea: str
    work_item_key: str
    max_questions: int
    max_review_rounds: int
    language: str = "en"
    auto_answer: bool = False


@dataclass
class BuiltPipeline:
    workflow: Workflow
    mermaid: str
    resources: list[Any] = field(default_factory=list)  # things to close when the run ends

    async def aclose(self) -> None:
        for resource in self.resources:
            close = getattr(resource, "aclose", None) or getattr(resource, "close", None)
            if close:
                result = close()
                if hasattr(result, "__await__"):
                    await result


def build_pipeline(
    settings: Settings, library: PromptLibrary, workspace: RunWorkspace, options: RunOptions, on_tool_call: OnCall
) -> BuiltPipeline:
    lang = options.language

    def agent(name: str, tools=None, **variables: str):
        return create_agent(
            settings, library, name, language=lang, on_tool_call=on_tool_call, tools=tools, variables=variables
        )

    # --- Agents: prompt file + tools, nothing else differs ------------------------------------------------------
    workspace_tools = WorkspaceTools(workspace)
    tracker = TrackerTools(settings)
    pr_tools = pull_request_tools(settings, options.work_item_key)
    interviewer = agent(INTERVIEWER, max_questions=str(options.max_questions))
    developer = agent(DEVELOPER, workspace_tools.developer_tools())
    tester = agent(TESTER, workspace_tools.tester_tools())
    release = agent(MERGE_REQUEST, [*pr_tools, *tracker.tools()])

    # --- Executors: the nodes of the graph ----------------------------------------------------------------------
    interview = InterviewerExecutor(interviewer, workspace, options.max_questions, lang)
    develop = DeveloperExecutor(developer, workspace)
    test = TesterExecutor(tester, workspace, options.max_review_rounds, lang)
    ship = MergeRequestExecutor(release, workspace, lang)

    # --- Edges ----------------------------------------------------------------------------------------------------
    # A cycle is fine in a workflow graph: this one terminates because the tester's NextStep policy is bounded by
    # max_review_rounds (and the builder's max_iterations is a backstop).
    workflow = (
        WorkflowBuilder(
            name="design-pipeline",
            description="Interview -> approve spec -> develop -> test (loop) -> merge request",
            start_executor=interview,
        )
        .add_edge(interview, develop)
        .add_edge(develop, test)
        .add_edge(test, develop, condition=lambda r: isinstance(r, ReviewOutcome) and r.next is NextStep.REWORK)
        .add_edge(test, ship, condition=lambda r: isinstance(r, ReviewOutcome) and r.next is NextStep.SHIP)
        # Observability: Agent Framework emits OpenTelemetry spans per super-step and executor once
        # agent_framework.observability is configured; with the agents' spans that is one trace per run.
        .build()
    )
    return BuiltPipeline(workflow, WorkflowViz(workflow).to_mermaid(), [tracker, *pr_tools])
