"""The "open a pull request" tool for the release agent: GitHub's MCP server, or (by default) a local stand-in with
the same name and parameters.

**What MCP buys you.** The Model Context Protocol lets a server publish tools (with schemas) that any MCP client can
discover at runtime. Agent Framework's `MCPStreamableHTTPTool` drops those tools straight into an agent's tool list
next to our own functions. You get GitHub's maintained tools without writing a client.

**What it costs.** A network hop per call, another credential, and a tool surface you do not control (GitHub's server
exposes about a hundred tools; putting all of them in the prompt wastes tokens and confuses smaller models). So we
**filter to the one tool we need** with `allowed_tools`.

**Switching it on.** `PIPELINE_GITHUB_MCP=true` plus `PIPELINE_GITHUB_TOKEN` (a fine-grained PAT with pull-request
write on the target repo). Nothing else in the pipeline changes: the prompt and the model's behaviour are the same.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

from ..config import Settings


def pull_request_tools(settings: Settings, work_item_key: str) -> list[Any]:
    if settings.github_mcp and settings.github_token:
        from agent_framework import MCPStreamableHTTPTool

        return [
            MCPStreamableHTTPTool(
                name="github",
                url=settings.github_mcp_url,
                static_headers={"Authorization": f"Bearer {settings.github_token}"},
                allowed_tools=["create_pull_request"],
                load_prompts=False,
            )
        ]

    @tool(
        name="create_pull_request",
        description="Create a pull request in a GitHub repository. (MOCK: nothing is sent to GitHub.)",
    )
    def create_pull_request(
        head: Annotated[str, Field(description="Branch containing the changes.")],
        base: Annotated[str, Field(description="Branch to merge into, usually 'main'.")],
        title: Annotated[str, Field(description="Pull request title.")],
        body: Annotated[str, Field(description="Pull request body, Markdown.")],
        draft: Annotated[bool, Field(description="Open as draft.")] = True,
    ) -> str:
        # Shaped like the real tool's result so downstream parsing is the same.
        return json.dumps({
            "number": 42,
            "html_url": f"https://github.com/{settings.github_owner}/{settings.github_repo}/pull/42",
            "state": "open", "draft": draft, "head": {"ref": head}, "base": {"ref": base}, "title": title,
            "body_preview": body if len(body) <= 120 else body[:120] + "...",
            "mocked": True, "work_item": work_item_key,
        })  # fmt: skip

    return [create_pull_request]
