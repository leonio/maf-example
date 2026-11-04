"""Markdown views of the contracts, for the files written to the run folder, and Markdown to HTML for the UI.

Presentation lives here rather than as methods on the models, so the JSON schema sent to the model stays exactly
the data we want, with no computed fields leaking into it. Headings follow the run's language.
"""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

from .contracts import MergeRequestPlan, RequirementsSpec, ReviewOutcome

# `html=False`: model-written Markdown cannot smuggle raw HTML (scripts, iframes) into the page.
_md = MarkdownIt("commonmark", {"html": False, "linkify": False}).enable("table")

HEADINGS = {
    "en": {
        "primary_user": "Primary user", "app_kind": "App kind", "user_stories": "User stories",
        "acceptance_criteria": "Acceptance criteria", "assumptions": "Assumptions", "out_of_scope": "Out of scope",
        "review": "Review - round {n}", "verdict": "Verdict", "next": "Next step", "findings": "Findings",
        "severity": "Severity", "file": "File", "finding": "Finding", "tests": "Tests written", "none": "_None._",
        "branch": "Branch", "pr": "Pull request", "not_created": "_not created_", "push": "Push it yourself",
        "notes": "Notes",
    },
    "de": {
        "primary_user": "Hauptnutzer", "app_kind": "Art der App", "user_stories": "User Stories",
        "acceptance_criteria": "Akzeptanzkriterien", "assumptions": "Annahmen", "out_of_scope": "Nicht im Umfang",
        "review": "Review - Runde {n}", "verdict": "Ergebnis", "next": "Nächster Schritt", "findings": "Befunde",
        "severity": "Schwere", "file": "Datei", "finding": "Befund", "tests": "Geschriebene Tests", "none": "_Keine._",
        "branch": "Branch", "pr": "Pull Request", "not_created": "_nicht angelegt_", "push": "Selbst pushen",
        "notes": "Hinweise",
    },
}  # fmt: skip


# GitHub-style task list items ("- [x] done") as ticks; CommonMark itself has no task lists.
_TASK = re.compile(r"<li>\[([ xX])\] ")


def to_html(markdown: str) -> str:
    return _TASK.sub(
        lambda m: '<li class="dp-task dp-task--done">' if m.group(1) != " " else '<li class="dp-task">',
        _md.render(markdown),
    )


def _list(h: dict[str, str], heading: str, items: list[str], checkbox: bool = False) -> list[str]:
    lines = [f"## {heading}", ""]
    lines += [f"- [ ] {i}" if checkbox else f"- {i}" for i in items] or [h["none"]]
    return [*lines, ""]


def spec_markdown(spec: RequirementsSpec, lang: str = "en") -> str:
    h = HEADINGS.get(lang, HEADINGS["en"])
    lines = [
        f"# {spec.title}", "", spec.summary, "",
        f"**{h['primary_user']}:** {spec.primary_user}  ", f"**{h['app_kind']}:** {spec.app_kind}", "",
    ]  # fmt: skip
    lines += _list(h, h["user_stories"], spec.user_stories)
    lines += _list(h, h["acceptance_criteria"], spec.acceptance_criteria, checkbox=True)
    lines += _list(h, h["assumptions"], spec.assumptions)
    lines += _list(h, h["out_of_scope"], spec.out_of_scope)
    return "\n".join(lines)


def review_markdown(outcome: ReviewOutcome, lang: str = "en") -> str:
    h = HEADINGS.get(lang, HEADINGS["en"])
    report = outcome.report
    lines = [
        f"# {h['review'].format(n=outcome.round)}", "",
        f"**{h['verdict']}:** {report.verdict}  ", f"**{h['next']}:** {outcome.next}", "",
        report.summary, "", f"## {h['findings']}", "",
    ]  # fmt: skip
    if not report.findings:
        lines.append(h["none"])
    else:
        lines += [f"| {h['severity']} | {h['file']} | {h['finding']} |", "| --- | --- | --- |"]
        for f in report.findings:
            severity = f"**{f.severity}**" if f.is_blocking else str(f.severity)
            lines.append(f"| {severity} | `{f.file}` | {f.message.replace('|', '\\|')} |")
    lines.append("")
    lines += _list(h, h["tests"], report.tests_written)
    return "\n".join(lines)


def merge_request_markdown(plan: MergeRequestPlan, lang: str = "en") -> str:
    h = HEADINGS.get(lang, HEADINGS["en"])
    lines = [
        f"# {plan.title}", "",
        f"**{h['branch']}:** `{plan.branch}`  ", f"**{h['pr']}:** {plan.pull_request_url or h['not_created']}", "",
        plan.body, "", f"## {h['push']}", "", "```bash", *plan.commands, "```", "",
    ]  # fmt: skip
    if plan.notes:
        lines += [f"## {h['notes']}", "", *[f"- {n}" for n in plan.notes], ""]
    return "\n".join(lines)
