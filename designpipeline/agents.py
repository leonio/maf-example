"""Turns a prompt file plus a tool list into an Agent Framework `Agent`.

`Agent` is the unit you run, compose into workflows, or expose as a tool to another agent. It owns the
instructions, tools, middleware and context providers, and runs the model/tool loop over any chat client.

Everything that makes the four agents *different* lives in data (their prompt file and tool list); this is the only
code that builds agents. Alternatives worth knowing:

* **Declarative agents** (`agent_framework.declarative`): agents and whole workflows defined in YAML. Great for
  low-code authoring; less flexible for custom tools and providers like ours.
* **Server-side agents** (Azure AI Foundry): the service stores instructions and threads, managed and versioned
  centrally.
* **Agent as tool** (`agent.as_tool()`): one agent calls another like a function (an "orchestrator"). We use an
  explicit workflow instead because the order of steps is known up front and should not be left to a model.
"""

from __future__ import annotations

from typing import Any

from agent_framework import Agent

from .config import Settings
from .llm import chat_client
from .prompts import PromptLibrary
from .rag import InstructionsContextProvider
from .tools.observed import OnCall, ToolCallObserver

LANGUAGES = {"en": "English", "de": "German"}


def create_agent(
    settings: Settings,
    library: PromptLibrary,
    name: str,
    *,
    language: str,
    on_tool_call: OnCall,
    tools: list[Any] | None = None,
    variables: dict[str, str] | None = None,
) -> Agent:
    prompt = library.get(name)
    options: dict[str, Any] = {}
    # Reasoning models (o-series, gpt-5) reject temperature; drop it from the front matter if you use one.
    if prompt.temperature is not None and not settings.is_mock:
        options["temperature"] = prompt.temperature
    return Agent(
        chat_client(settings, name),
        instructions=library.compose(prompt, {"language": LANGUAGES.get(language, "English"), **(variables or {})}),
        name=name,
        description=prompt.description,
        tools=tools or None,
        default_options=options or None,
        # Per-agent RAG over instructions/ (see rag.py for the production shape).
        context_providers=[InstructionsContextProvider(library, prompt.pinned_instructions)],
        middleware=[ToolCallObserver(name, on_tool_call)],
    )
