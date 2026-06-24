# Quality Gate Prompt

Run this prompt to execute the fast quality gate before submitting changes.

1. Run `uv run ruff check .` — fix any violations.
2. Run `uv run ruff format --check .` — fix any formatting issues.
3. Run `uv run pytest -q` — ensure all tests pass.
4. If changes are security-sensitive, run `uv run bandit -r src`.

Report:
- Files modified
- Commands run and their exit codes
- Any warnings or failures
