# Python coding standards

## Language level
Target Python 3.12+. Use type hints everywhere, `dataclasses` (or Pydantic at
the edges) for data, `pathlib` for paths, `match` for command dispatch and
f-strings for formatting. Keep modules small and functions short.

## Typing
Annotate every public function. Prefer `X | None` to `Optional[X]` and built-in
generics (`list[str]`) to `typing.List`. Never silence the type checker without
a comment saying why.

## Async
Only use `async` where there is real I/O to overlap. Never call `asyncio.run`
inside library code, and never block the event loop with `time.sleep`.

## Command-line apps
Keep `main.py` thin: parse arguments with `argparse`, build objects, call one
entry point, return an exit code. Put logic in modules that never `print`, so
they can be unit tested.

## Errors
Validate input at the edge and return a friendly message plus a non-zero exit
code. Raise specific exceptions (`ValueError`, `LookupError`); do not catch
`Exception` except at the top level.

## Storage
For small apps a JSON file via the `json` module is fine. Write atomically:
write to a temporary file in the same folder, then `Path.replace` it over the
original.
