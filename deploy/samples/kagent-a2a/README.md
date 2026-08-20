# kagent A2A Role Examples

Educational agent manifests for the E1–E5 sequence. See
[Project North Star](../../../docs/north-star.md) and
[kagent A2A examples runbook](../../../docs/runbooks/kagent-a2a-examples.md).

| Directory | Role focus | Example |
|-----------|------------|---------|
| `01-planner/` | Planner agent | E1 |
| `02-reviewer/` | Reviewer agent | Phase 2 (manual coordination) |
| `03-supervisor/` | Supervisor + Agent-tool delegation | E2 |
| `04-docs-agent/` | Docs validator | E3 (future) |
| `05-telegram-capstone/` | Full capstone | E5 (future) |

**Status:** E1–E2 manifests and harness land in PR #4 (`edu/kagent-a2a-role-examples`).

These are `deploy/samples/` educational starters, not production base resources.

Apply order for E1–E2:

```text
ide-safe-deepseek-model-config → planner-agent → reviewer-agent → supervisor-agent
```

Harness:

```text
scripts/kagent/experiments/run_a2a_example.py
scripts/kagent/experiments/record_experiment.py
```
