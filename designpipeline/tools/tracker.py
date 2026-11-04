"""Keep the paperwork in sync: minimal Jira Cloud (REST v3) and Confluence Cloud (REST v2) clients, a fake
Atlassian for offline runs, and the three tools the release agent gets.

**Why hand-written clients instead of an SDK?** Agent tools should be narrow. Three functions with clear names make
better tools than a generated client with 600 operations, and they keep the blast radius of a misbehaving model
small. The tool functions are thin adapters: the clients stay reusable (and testable) outside of AI, and the tool
layer owns the model-facing decisions, such as which parameters the model may choose (issue key yes; the
Confluence page id no: it comes from configuration, so the model cannot be talked into editing an arbitrary page).

**Why mock at the transport?** `httpx.MockTransport` answers in-process, so everything above it (URL building,
JSON shaping, error handling, the tool wrapper, the model's tool call) runs exactly as it would against Atlassian.
Set `PIPELINE_JIRA_USE_MOCK=false` plus a token to hit the real API.

**Human approval for side effects.** These calls change shared systems. In production consider
`tool(..., approval_mode="always_require")`: the agent run then pauses with an approval request that a workflow can
surface to the UI, exactly like the spec approval gate.
"""

from __future__ import annotations

import html
import json
from typing import Annotated

import httpx
from agent_framework import FunctionTool, tool
from pydantic import Field

from ..config import Atlassian, Settings


class JiraClient:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def add_comment(self, issue_key: str, text: str) -> str:
        # Jira v3 wants Atlassian Document Format (ADF), not plain text.
        adf = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": line}]}
                    for line in text.split("\n")
                    if line.strip()
                ],
            }
        }
        response = await self.http.post(f"rest/api/3/issue/{issue_key}/comment", json=adf)
        response.raise_for_status()
        return f"Comment {response.json().get('id')} added to {issue_key}."

    async def transition(self, issue_key: str, name: str) -> str:
        # Transitions are looked up by *name*: transition ids differ per workflow and per project, and hard-coding
        # "31" is a classic Jira-integration bug.
        path = f"rest/api/3/issue/{issue_key}/transitions"
        available = (await self.http.get(path)).raise_for_status().json().get("transitions", [])
        match = next((t for t in available if t.get("name", "").lower() == name.lower()), None)
        if match is None:
            names = ", ".join(t.get("name", "") for t in available)
            return f"ERROR: '{name}' is not available for {issue_key}. Available: {names}."
        (await self.http.post(path, json={"transition": {"id": match["id"]}})).raise_for_status()
        return f"{issue_key} moved to '{name}'."


class ConfluenceClient:
    """Confluence uses optimistic concurrency: an update must carry `version.number = current + 1` or it is rejected
    with 409, so "update a page" is always read-modify-write. On a 409 the right fix is to re-read and retry once."""

    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def append_section(self, page_id: str, heading: str, text: str) -> str:
        page = (
            (await self.http.get(f"wiki/api/v2/pages/{page_id}", params={"body-format": "storage"}))
            .raise_for_status()
            .json()
        )
        version = page["version"]["number"]
        existing = page.get("body", {}).get("storage", {}).get("value", "")
        # Storage format is XHTML; the agent's text becomes plain paragraphs.
        paragraphs = "".join(f"<p>{html.escape(line.lstrip('- '))}</p>" for line in text.split("\n") if line.strip())
        body = f"{existing}<h2>{html.escape(heading)}</h2>{paragraphs}"
        payload = {
            "id": page_id,
            "status": "current",
            "title": page["title"],
            "body": {"representation": "storage", "value": body},
            "version": {"number": version + 1, "message": "Updated by release agent"},
        }
        (await self.http.put(f"wiki/api/v2/pages/{page_id}", json=payload)).raise_for_status()
        return f"Page '{page['title']}' updated to version {version + 1}."


class FakeAtlassian:
    """Answers the handful of routes the clients use, with realistic payloads. One per run."""

    def __init__(self) -> None:
        self.page_version = 7

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if method == "POST" and path.endswith("/comment"):
            return httpx.Response(201, json={"id": "10042", "self": f"{request.url}/10042"})
        if method == "GET" and path.endswith("/transitions"):
            names = ["To Do", "In Progress", "In Review", "Done"]
            return httpx.Response(
                200, json={"transitions": [{"id": str(11 + 10 * i), "name": n} for i, n in enumerate(names)]}
            )
        if method == "POST" and path.endswith("/transitions"):
            return httpx.Response(204)
        if method == "GET" and "/wiki/api/v2/pages/" in path:
            return httpx.Response(200, json={
                "id": path.rsplit("/", 1)[-1], "title": "Team Apps - Release Notes",
                "version": {"number": self.page_version}, "body": {"storage": {"value": "<p>Existing content.</p>"}},
            })  # fmt: skip
        if method == "PUT" and "/wiki/api/v2/pages/" in path:
            self.page_version += 1
            return httpx.Response(200, json={"id": path.rsplit("/", 1)[-1], "version": {"number": self.page_version}})
        return httpx.Response(404, json={"errorMessages": [f"Fake Atlassian has no route for {method} {path}"]})


def _client(options: Atlassian, fake: FakeAtlassian) -> httpx.AsyncClient:
    # Atlassian Cloud basic auth = email + API token. For apps acting on behalf of users, use OAuth 2.0 (3LO).
    return httpx.AsyncClient(
        base_url=options.base_url.rstrip("/") + "/",
        auth=(options.email, options.api_token or ""),
        headers={"Accept": "application/json"},
        transport=httpx.MockTransport(fake) if options.use_mock else None,
        timeout=30,
    )


# Module level: tool schemas are built from the annotations, which must resolve outside the function.
Key = Annotated[str, Field(description="Work item key, e.g. DEMO-123.")]


class TrackerTools:
    def __init__(self, settings: Settings):
        fake = FakeAtlassian()
        self._http = [_client(settings.jira, fake), _client(settings.confluence, fake)]
        self.jira = JiraClient(self._http[0])
        self.confluence = ConfluenceClient(self._http[1])
        self.page_id = settings.confluence_page_id

    async def aclose(self) -> None:
        for http in self._http:
            await http.aclose()

    def tools(self) -> list[FunctionTool]:
        async def guard(call) -> str:
            # Turns transport failures into a message the model can act on (and the run can survive).
            try:
                return await call
            except httpx.HTTPStatusError as e:
                return f"ERROR: {e.response.status_code} - {e.response.text[:200]}"
            except httpx.HTTPError as e:
                return f"ERROR: network - {e}"

        @tool(name="jira_add_comment", description="Add a comment to a Jira work item.")
        async def jira_add_comment(
            issue_key: Key,
            comment: Annotated[str, Field(description="Comment text. Plain text, one paragraph per line.")],
        ) -> str:
            return await guard(self.jira.add_comment(issue_key, comment))

        @tool(
            name="jira_transition_issue",
            description="Move a Jira work item to another status, by transition name (e.g. 'In Review').",
        )
        async def jira_transition_issue(
            issue_key: Key, transition_name: Annotated[str, Field(description="Transition name, e.g. 'In Review'.")]
        ) -> str:
            return await guard(self.jira.transition(issue_key, transition_name))

        @tool(
            name="confluence_update_page", description="Append a section to the team's Confluence release-notes page."
        )
        async def confluence_update_page(
            heading: Annotated[str, Field(description="Section heading, e.g. 'DEMO-123: Team Task Tracker'.")],
            content: Annotated[str, Field(description="Section content. Plain text, one bullet per line.")],
        ) -> str:
            return await guard(self.confluence.append_section(self.page_id, heading, content))

        return [jira_add_comment, jira_transition_issue, confluence_update_page]


def shorten(value: object, limit: int = 60) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
