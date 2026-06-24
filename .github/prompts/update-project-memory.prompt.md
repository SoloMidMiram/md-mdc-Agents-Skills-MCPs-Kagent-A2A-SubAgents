# Update Project Memory Prompt

Use this when you discover a reusable lesson, recurring bug pattern,
or durable architecture decision.

1. Read the existing files under `.project-ai/memory/`.
2. Determine which file(s) to update:
   - `recurring-bugs.md` — a defect pattern that appeared more than once
   - `architecture-decisions.md` — a durable design choice
   - `python-risks.md` — a Python-specific risk or gotcha
   - `kubernetes-risks.md` — a deployment or cluster risk
   - `dependency-notes.md` — a dependency constraint or incompatibility
   - `diagnostics.md` — a proven diagnostic procedure
   - `release-diary.md` — a release outcome worth recording
3. Append a dated entry with:
   - Date (YYYY-MM-DD)
   - Context (what happened, why it matters)
   - Resolution or decision
   - Cross-reference to relevant code or issues

Do not add entries for one-time fixes or trivial observations.
