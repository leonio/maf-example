---
name: code-review
description: Lightweight checklist for reviewing a small Python codebase against its spec.
---
# Code review checklist

Rate each finding `High`, `Medium` or `Low`.

| Area | Ask | Typical severity |
| --- | --- | --- |
| Spec | Is every acceptance criterion implemented? | High |
| Correctness | Off-by-one, `None` handling, empty and whitespace input, encoding of files | High |
| Input | Is user input validated with a helpful message? | Medium |
| Errors | Are exceptions caught at the edge and reported, not swallowed or shown as a traceback? | Medium |
| Structure | Is logic separated from I/O (`print`, `argparse`, files) so it can be tested? | Medium |
| Modern Python | type hints, dataclasses, `pathlib`, `match`; no mutable default arguments | Low |
| Docs | Does the README say how to run it? | Low |

Keep findings actionable: *file, what is wrong, what to do instead*.
