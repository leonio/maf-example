"""The words the scripted model says, in English and German. Whatever idea you type, it builds the same app."""

QUESTIONS = {
    "en": [
        ("Who will use this day to day?",
         "Everything else (interface, permissions, wording) depends on who the user is.",
         ["Just me, as a personal tool", "My small team (2-10 people)", "Anyone in the company"]),
        ("If it could only do one thing on day one, what would that be?",
         "This becomes the core user story; everything else can wait for v2.",
         ["Add tasks and list what is open", "Assign tasks to people", "Track due dates"]),
        ("Where should the tasks be kept between runs?",
         "Storage drives both the design and what can go wrong.",
         ["A local JSON file", "SQLite", "In memory only"]),
        ("What should happen if someone adds a task with an empty title?",
         "Edge cases like this become acceptance criteria and tests.",
         ["Reject it with a clear error", "Save it as 'Untitled'", "Ignore it silently"]),
    ],
    "de": [
        ("Wer wird das im Alltag benutzen?",
         "Alles andere (Oberfläche, Berechtigungen, Formulierungen) hängt davon ab, wer die Nutzer sind.",
         ["Nur ich, als persönliches Werkzeug", "Mein kleines Team (2-10 Personen)", "Alle im Unternehmen"]),
        ("Wenn es am ersten Tag nur eine Sache könnte: welche?",
         "Das wird die zentrale User Story; alles andere kann bis Version 2 warten.",
         ["Aufgaben anlegen und offene auflisten", "Aufgaben Personen zuweisen", "Fälligkeiten verfolgen"]),
        ("Wo sollen die Aufgaben zwischen zwei Aufrufen gespeichert werden?",
         "Die Speicherung bestimmt den Entwurf und was schiefgehen kann.",
         ["In einer lokalen JSON-Datei", "In SQLite", "Nur im Arbeitsspeicher"]),
        ("Was soll passieren, wenn jemand eine Aufgabe ohne Titel anlegt?",
         "Solche Randfälle werden zu Akzeptanzkriterien und Tests.",
         ["Mit einer klaren Fehlermeldung ablehnen", "Als 'Ohne Titel' speichern", "Stillschweigend ignorieren"]),
    ],
}  # fmt: skip

SPEC = {
    "en": dict(
        title="Team Task Tracker CLI",
        summary="A tiny command-line tool a small team uses to add tasks, list open ones and mark them done. Tasks are kept in a local JSON file.",
        primary_user="Members of a small team (2-10 people) sharing one machine or repo",
        app_kind="cli",
        user_stories=[
            "As a team member, I want to add a task with a title, so that it is not forgotten.",
            "As a team member, I want to list open tasks, so that I know what is left to do.",
            "As a team member, I want to mark a task as done, so that the list stays current.",
        ],
        acceptance_criteria=[
            "Given an empty store, when I run `add \"Write docs\"`, then `list` shows one open task 'Write docs' with id 1.",
            "Given a task with id 1, when I run `done 1`, then `list` no longer shows it.",
            'When I run `add ""` (empty or whitespace title), then I see an error and nothing is saved.',
            "Tasks survive between runs (stored in tasks.json next to main.py).",
        ],
        assumptions=["Single user at a time; no file locking.", "No due dates or assignees in v1."],
        out_of_scope=["Assigning tasks to people", "Due dates and reminders", "A web or GUI front end"],
    ),
    "de": dict(
        title="Team-Aufgabenliste (CLI)",
        summary="Ein kleines Kommandozeilenwerkzeug, mit dem ein kleines Team Aufgaben anlegt, offene auflistet und erledigte abhakt. Die Aufgaben liegen in einer lokalen JSON-Datei.",
        primary_user="Mitglieder eines kleinen Teams (2-10 Personen), die sich einen Rechner oder ein Repository teilen",
        app_kind="cli",
        user_stories=[
            "Als Teammitglied möchte ich eine Aufgabe mit Titel anlegen, damit sie nicht vergessen wird.",
            "Als Teammitglied möchte ich die offenen Aufgaben sehen, damit ich weiß, was noch zu tun ist.",
            "Als Teammitglied möchte ich eine Aufgabe als erledigt markieren, damit die Liste aktuell bleibt.",
        ],
        acceptance_criteria=[
            "Bei leerem Speicher zeigt `list` nach `add \"Write docs\"` genau eine offene Aufgabe 'Write docs' mit der Nummer 1.",
            "Gibt es eine Aufgabe mit der Nummer 1, zeigt `list` sie nach `done 1` nicht mehr an.",
            'Bei `add ""` (leerer Titel oder nur Leerzeichen) erscheint eine Fehlermeldung und nichts wird gespeichert.',
            "Aufgaben bleiben zwischen zwei Aufrufen erhalten (gespeichert in tasks.json neben main.py).",
        ],
        assumptions=[
            "Immer nur eine Person gleichzeitig; keine Dateisperren.",
            "Keine Fälligkeiten oder Zuständigen in Version 1.",
        ],
        out_of_scope=[
            "Aufgaben Personen zuweisen",
            "Fälligkeiten und Erinnerungen",
            "Eine Web- oder grafische Oberfläche",
        ],
    ),
}

REVISED = {"en": "Revised after stakeholder feedback: {reason}", "de": "Überarbeitet nach Rückmeldung: {reason}"}

DEVELOPER = {
    "en": {
        "first": ("Implemented a Python 3.12 command-line app with add/list/done commands. Tasks are dataclasses persisted to tasks.json with the json module.",
                  ["Ids are sequential integers starting at 1."]),
        "fix": ("Fixed the tester's findings: TaskStore.add now rejects empty or whitespace titles with a ValueError, and main.py reports it as a friendly error with exit code 1.", []),
    },
    "de": {
        "first": ("Eine Kommandozeilen-App in Python 3.12 mit den Befehlen add, list und done umgesetzt. Aufgaben sind Dataclasses und werden mit dem json-Modul in tasks.json gespeichert.",
                  ["Die Nummern sind fortlaufende Ganzzahlen ab 1."]),
        "fix": ("Die Befunde des Testers behoben: TaskStore.add lehnt leere Titel oder Titel nur aus Leerzeichen mit einem ValueError ab, und main.py meldet das als verständlichen Fehler mit Exit-Code 1.", []),
    },
}  # fmt: skip

TESTER = {
    "en": {
        "approved": "All four acceptance criteria are implemented. Empty titles are now rejected before anything is saved. Tests cover add, done, empty-title rejection and persistence.",
        "low": "save() writes tasks.json directly; write to a temp file and replace it to avoid a corrupt file on crash (see coding standards > Storage).",
        "changes": 'Add/list/done work, but the empty-title acceptance criterion is not met: TaskStore.add accepts "" and saves it.',
        "high": "add() does not validate the title. Reject empty or whitespace titles with ValueError before changing any state.",
        "medium": "No error handling around add; an exception prints a traceback. Catch ValueError, print a friendly message and return exit code 1.",
    },
    "de": {
        "approved": "Alle vier Akzeptanzkriterien sind umgesetzt. Leere Titel werden jetzt abgelehnt, bevor etwas gespeichert wird. Die Tests decken Anlegen, Erledigen, das Ablehnen leerer Titel und die Speicherung ab.",
        "low": "save() schreibt tasks.json direkt; besser in eine temporäre Datei schreiben und sie ersetzen, damit ein Absturz keine kaputte Datei hinterlässt (siehe Coding Standards > Storage).",
        "changes": 'Anlegen, Auflisten und Erledigen funktionieren, aber das Kriterium zu leeren Titeln ist nicht erfüllt: TaskStore.add nimmt "" an und speichert es.',
        "high": "add() prüft den Titel nicht. Leere Titel oder Titel nur aus Leerzeichen mit ValueError ablehnen, bevor sich etwas ändert.",
        "medium": "Keine Fehlerbehandlung um add; eine Ausnahme gibt einen Traceback aus. ValueError abfangen, eine verständliche Meldung ausgeben und Exit-Code 1 zurückgeben.",
    },
}  # fmt: skip

MERGE_REQUEST = {
    "en": {
        "title": "{key}: Add Team Task Tracker CLI",
        "pr_body": "## Summary\nAdds a small CLI to add, list and complete tasks.\n\n## Review\nApproved by Tester.",
        "jira": "Team Task Tracker CLI implemented and reviewed (Approved).\nDraft PR opened: {branch}",
        "wiki_heading": "{key}: Team Task Tracker CLI",
        "wiki": "- New command-line app: add, list, done\n- Tasks stored in tasks.json\n- Empty titles rejected",
        "body": """## Summary
Adds **Team Task Tracker CLI**, a Python 3.12 command-line app to add, list and complete tasks stored in `tasks.json`.

## Acceptance criteria
- [x] `add` then `list` shows the task with id 1
- [x] `done 1` removes it from the open list
- [x] Empty titles are rejected and nothing is saved
- [x] Tasks persist between runs

## Review
Approved by Tester after one rework round. One open `Low` finding (atomic file writes).

## How to test
```bash
python -m unittest discover -s tests
python main.py add "Write docs" && python main.py list
```""",
        "note": "create_pull_request was mocked; run the commands above to push for real.",
    },
    "de": {
        "title": "{key}: Team-Aufgabenliste (CLI) hinzufügen",
        "pr_body": "## Zusammenfassung\nFügt ein kleines CLI zum Anlegen, Auflisten und Erledigen von Aufgaben hinzu.\n\n## Review\nVom Tester freigegeben.",
        "jira": "Team-Aufgabenliste (CLI) umgesetzt und geprüft (freigegeben).\nDraft-PR eröffnet: {branch}",
        "wiki_heading": "{key}: Team-Aufgabenliste (CLI)",
        "wiki": "- Neue Kommandozeilen-App: add, list, done\n- Aufgaben in tasks.json gespeichert\n- Leere Titel werden abgelehnt",
        "body": """## Zusammenfassung
Fügt die **Team-Aufgabenliste (CLI)** hinzu, eine Kommandozeilen-App in Python 3.12 zum Anlegen, Auflisten und Erledigen von Aufgaben in `tasks.json`.

## Akzeptanzkriterien
- [x] Nach `add` zeigt `list` die Aufgabe mit der Nummer 1
- [x] Nach `done 1` ist sie nicht mehr in der offenen Liste
- [x] Leere Titel werden abgelehnt und nichts wird gespeichert
- [x] Aufgaben bleiben zwischen zwei Aufrufen erhalten

## Review
Nach einer Nacharbeitsrunde vom Tester freigegeben. Ein offener Befund der Stufe `Low` (atomares Schreiben der Datei).

## So testen
```bash
python -m unittest discover -s tests
python main.py add "Write docs" && python main.py list
```""",
        "note": "create_pull_request war simuliert; mit den Befehlen oben wird wirklich gepusht.",
    },
}  # fmt: skip
