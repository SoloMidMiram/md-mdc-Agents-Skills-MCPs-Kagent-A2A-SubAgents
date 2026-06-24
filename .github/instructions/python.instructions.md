---
name: Python quality
description: Python engineering, test and typing rules
applyTo: "**/*.py"
---

# Python rules

- Use type hints on public functions and methods.
- Prefer small, testable functions.
- Use structured logging rather than `print` in application code.
- Do not catch `Exception` without adding context or re-raising appropriately.
- Add a regression test for every fixed defect.
- Keep I/O at boundaries and business logic in pure functions where practical.
- Run:

  `uv run ruff check .`
  `uv run ruff format --check .`
  `uv run mypy src`
  `uv run pytest`
