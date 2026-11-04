"""The source files the scripted developer and tester "write".

The generated app genuinely runs, and once the rework round has fixed the bug its tests pass:

    cd output/<run>/app
    python main.py add "Write docs" && python main.py list
    python -m unittest discover -s tests

Standard library only, so it runs anywhere Python 3.12 does. The first version has a deliberate bug (empty titles
are accepted) so the offline run shows the tester catching it and the developer fixing it.
"""

TASKS = '''\
"""Domain logic for the team task tracker: no printing, no argument parsing, so it can be tested on its own."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Task:
    id: int
    title: str
    done: bool = False


class TaskStore:
    def __init__(self, path: Path, tasks: list[Task] | None = None):
        self.path = path
        self.tasks = tasks or []

    @classmethod
    def load(cls, path: Path) -> TaskStore:
        if not path.exists():
            return cls(path)
        return cls(path, [Task(**t) for t in json.loads(path.read_text(encoding="utf-8"))])

    @property
    def open(self) -> list[Task]:
        return [t for t in self.tasks if not t.done]

    def add(self, title: str) -> Task:
        task = Task(id=max((t.id for t in self.tasks), default=0) + 1, title=title.strip())
        self.tasks.append(task)
        return task

    def complete(self, task_id: int) -> bool:
        for task in self.tasks:
            if task.id == task_id and not task.done:
                task.done = True
                return True
        return False

    def save(self) -> None:
        self.path.write_text(json.dumps([asdict(t) for t in self.tasks], indent=2), encoding="utf-8")
'''

TASKS_FIXED = TASKS.replace(
    """    def add(self, title: str) -> Task:
        task = """,
    """    def add(self, title: str) -> Task:
        if not title or not title.strip():
            raise ValueError("A task needs a title.")
        task = """,
)

MAIN = '''\
"""Team task tracker: python main.py add "Write docs" | list | done 1"""

import argparse
from pathlib import Path

from tasks import TaskStore

STORE = Path(__file__).resolve().parent / "tasks.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tasks", description="A tiny task tracker for a small team.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("add", help="add a task").add_argument("title")
    commands.add_parser("list", help="list open tasks")
    commands.add_parser("done", help="mark a task as done").add_argument("id", type=int)
    args = parser.parse_args(argv)

    store = TaskStore.load(STORE)
    match args.command:
        case "add":
            task = store.add(args.title)
            store.save()
            print(f"Added #{task.id}: {task.title}")
        case "list":
            for task in store.open:
                print(f"#{task.id:<3} {task.title}")
        case "done":
            if not store.complete(args.id):
                print(f"No open task #{args.id}.")
                return 1
            store.save()
            print(f"Done #{args.id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

MAIN_FIXED = MAIN.replace(
    """    store = TaskStore.load(STORE)
    match args.command:
        case "add":
            task = store.add(args.title)
""",
    """    store = TaskStore.load(STORE)
    match args.command:
        case "add":
            try:
                task = store.add(args.title)
            except ValueError as error:
                print(f"Error: {error}")
                return 1
""",
)

README = """\
# Team Task Tracker CLI

A tiny command-line tool a small team uses to add tasks, list open ones and mark them done.
Tasks are kept in `tasks.json` next to `main.py`. Python 3.12+, standard library only.

```bash
python main.py add "Write docs"
python main.py list
python main.py done 1
```

## Tests

```bash
python -m unittest discover -s tests
```
"""

TESTS = """\
import tempfile
import unittest
from pathlib import Path

from tasks import TaskStore


class TaskStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "tasks.json"

    def tearDown(self) -> None:
        self.folder.cleanup()

    def test_adding_a_task_to_an_empty_store_lists_it_with_id_1(self) -> None:
        store = TaskStore.load(self.path)
        store.add("Write docs")
        self.assertEqual([(t.id, t.title) for t in store.open], [(1, "Write docs")])

    def test_a_completed_task_is_no_longer_listed(self) -> None:
        store = TaskStore.load(self.path)
        store.add("Write docs")
        self.assertTrue(store.complete(1))
        self.assertEqual(store.open, [])

    def test_adding_a_task_with_an_empty_title_is_rejected(self) -> None:
        store = TaskStore.load(self.path)
        with self.assertRaises(ValueError):
            store.add("")
        self.assertEqual(store.tasks, [])

    def test_adding_a_task_with_a_whitespace_title_is_rejected(self) -> None:
        store = TaskStore.load(self.path)
        with self.assertRaises(ValueError):
            store.add("   ")

    def test_tasks_survive_between_runs(self) -> None:
        store = TaskStore.load(self.path)
        store.add("Write docs")
        store.save()
        self.assertEqual([t.title for t in TaskStore.load(self.path).open], ["Write docs"])


if __name__ == "__main__":
    unittest.main()
"""
