"""A deliberately tiny Retrieval-Augmented Generation hook over `instructions/`.

Before every agent call, find the instruction sections most relevant to what the agent is being asked and add them
to the system instructions for that call only.

**Where it plugs in.** `ContextProvider.before_run` is Agent Framework's extension point that runs before each
agent invocation; whatever it adds to the `SessionContext` (instructions, messages, tools) is merged into that one
request. It is registered per agent (`Agent(..., context_providers=[...])`), so each agent has its own sources.

**Why not pin every document?** Pinning (`instructions:` in a prompt's front matter) is right for the two or three
rules an agent must always follow. Once the corpus grows (every ADR, every wiki page about the domain), pinning
blows the context window and dilutes attention; retrieval sends only what matters for this turn.

**Why keyword scoring and not embeddings?** So the app runs offline with no infrastructure. The production
shape swaps `search` for a vector search (an embedding client plus a vector store) and keeps everything else.

**Security:** anything retrieved is injected into the model's instructions. Only index sources you trust as much as
your own prompts; treat wiki or ticket content as data (a clearly delimited user message), not as instructions.
"""

from __future__ import annotations

from agent_framework import ContextProvider

from .prompts import WORD, InstructionSection, PromptLibrary

STOP_WORDS = {
    "this", "that", "with", "from", "have", "what", "when", "will", "your", "must", "should", "there", "their",
    "they", "about", "into", "only", "each", "every", "than", "then", "were",
}  # fmt: skip


def _tokens(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if len(w) > 3 and w not in STOP_WORDS}


class InstructionsContextProvider(ContextProvider):
    def __init__(self, library: PromptLibrary, pinned: list[str], top: int = 2):
        super().__init__("instructions-rag")
        self.library = library
        self.pinned = set(pinned)
        self.top = top

    async def before_run(self, *, agent, session, context, state) -> None:
        # Query = the text of what the agent is being asked right now.
        query = " ".join(m.text for m in context.input_messages if m.role == "user" and m.text)
        hits = self.search(query)
        if not hits:
            return
        lines = ["# Retrieved guidance (most relevant sections of the team's standing instructions)", ""]
        for hit in hits:
            # Cite the source so the model (and a human reading logs) can tell where it came from.
            lines += [f"## {hit.heading} _(from instructions/{hit.document}.md)_", hit.text, ""]
        context.extend_instructions(self.source_id, "\n".join(lines))

    def search(self, query: str) -> list[InstructionSection]:
        terms = _tokens(query)
        if not terms:
            return []
        scored = [
            (len(_tokens(f"{s.heading} {s.heading} {s.text}") & terms), s)
            for doc in self.library.instructions
            if doc.name not in self.pinned  # pinned docs are already in context
            for s in doc.sections
        ]
        scored = [x for x in scored if x[0] >= 2]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[: self.top]]
