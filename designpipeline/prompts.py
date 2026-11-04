"""Loads the three kinds of authored content this app keeps outside of Python.

| Folder           | Granularity        | Question it answers                                  |
| ---------------- | ------------------ | ---------------------------------------------------- |
| `prompts/`       | one per agent      | Who am I, what do I do, what do I return?            |
| `skills/<name>/` | reusable procedure | How do I do this kind of task? (SKILL.md layout)     |
| `instructions/`  | org-wide rules     | What rules apply here? (pinned, or retrieved by RAG) |

Why files and not string constants? The people who should tune an interviewer's tone or a review checklist are
rarely the people who deploy the app. Files diff well, can be owned via CODEOWNERS, and are re-read for every run,
so an edit takes effect on the next run without a restart.

Front matter is parsed by hand: we only need `key: value` and `key: [a, b]`. PyYAML is the right call as soon as
you need nesting or multi-line values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptDefinition:
    agent: str
    description: str
    body: str  # the system prompt itself, may contain {{placeholders}}
    skills: list[str]
    pinned_instructions: list[str]
    temperature: float | None


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    description: str
    body: str


@dataclass(frozen=True)
class InstructionSection:
    document: str
    heading: str
    text: str


@dataclass(frozen=True)
class InstructionDocument:
    name: str
    title: str
    sections: list[InstructionSection]


class PromptLibrary:
    def __init__(self, root: Path):
        self.prompts = {p.agent: p for p in map(_parse_prompt, sorted((root / "prompts").glob("*.md")))}
        self.skills = {s.name: s for s in map(_parse_skill, sorted((root / "skills").glob("*/SKILL.md")))}
        self.instructions = [_parse_instruction(p) for p in sorted((root / "instructions").glob("*.md"))]

    def get(self, agent: str) -> PromptDefinition:
        try:
            return self.prompts[agent]
        except KeyError:
            raise LookupError(f"No prompt found for agent '{agent}'. Expected prompts/{agent}.md.") from None

    def compose(self, prompt: PromptDefinition, variables: dict[str, str] | None = None) -> str:
        """Prompt body (placeholders filled) + each referenced skill + each pinned instruction document.

        Order matters: models weight the start and end of a system prompt most, so the persona and output contract
        go first and the long reference material last.
        """
        body = prompt.body
        for key, value in (variables or {}).items():
            body = body.replace("{{" + key + "}}", value)
        parts = [body.strip(), ""]

        for name in prompt.skills:
            skill = self.skills.get(name)
            if skill is None:
                raise LookupError(f"Prompt '{prompt.agent}' references unknown skill '{name}'.")
            parts += [f"# Skill: {skill.name}", "", skill.body.strip(), ""]

        for name in prompt.pinned_instructions:
            doc = next((d for d in self.instructions if d.name == name), None)
            if doc is None:
                raise LookupError(f"Prompt '{prompt.agent}' pins unknown instructions '{name}'.")
            parts += [f"# Standing instructions: {doc.title}", ""]
            for section in doc.sections:
                parts += [f"## {section.heading}", section.text, ""]

        return "\n".join(parts)


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[4:end].split("\n"):
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip().lower()] = value.strip()
    return meta, text[end + 4 :].lstrip("\n")


def _list(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").strip("[]").split(",") if v.strip()]


def _parse_prompt(path: Path) -> PromptDefinition:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
    try:
        temperature = float(meta["temperature"]) if "temperature" in meta else None
    except ValueError:
        temperature = None
    return PromptDefinition(
        agent=meta.get("agent") or path.stem,
        description=meta.get("description", ""),
        body=body,
        skills=_list(meta.get("skills")),
        pinned_instructions=_list(meta.get("instructions")),
        temperature=temperature,
    )


def _parse_skill(path: Path) -> SkillDefinition:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
    return SkillDefinition(meta.get("name") or path.parent.name, meta.get("description", ""), body)


def _parse_instruction(path: Path) -> InstructionDocument:
    """Chunk by `## ` heading. For RAG, *how you chunk* usually matters more than which vector database you pick: a
    heading-sized chunk is self-contained and citeable."""
    lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), path.stem)
    sections: list[InstructionSection] = []
    heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if heading is not None:
            sections.append(InstructionSection(path.stem, heading, "\n".join(buffer).strip()))

    for line in lines:
        if line.startswith("## "):
            flush()
            heading, buffer = line[3:].strip(), []
        elif heading is not None:
            buffer.append(line)
    flush()
    return InstructionDocument(path.stem, title, sections)


WORD = re.compile(r"[a-z][a-z0-9\-]+")
