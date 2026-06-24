# Diagnose Failure Prompt

Use this when a test, build, or deployment fails unexpectedly.

1. Read the exact error message and exit code.
2. Inspect the relevant source files and recent changes.
3. Check `.project-ai/memory/recurring-bugs.md` and `.project-ai/memory/diagnostics.md`
   for known patterns.
4. Search the repository for similar error patterns.
5. Propose a fix with a regression test.
6. If the cause is not immediately clear, add a diagnostics entry to
   `.project-ai/memory/diagnostics.md`.

Report:
- Error message
- Root cause hypothesis
- Fix applied
- Regression test result
