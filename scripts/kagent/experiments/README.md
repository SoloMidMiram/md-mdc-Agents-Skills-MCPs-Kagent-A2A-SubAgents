# kagent A2A Experiment Harness

Scripts for Lane A education (PR #4) and Lane B benchmarking (PR #6). See
[Project North Star](../../../docs/north-star.md).

| Script | Purpose | Target PR |
|--------|---------|-----------|
| `run_a2a_example.py` | Single-role A2A dispatch with contract validation | #4 |
| `record_experiment.py` | Sanitized evidence JSON writer | #4 |
| `contracts.py` | Planner/reviewer/supervisor JSON contracts | #4 |
| `benchmark_a2a.py` | Baselines B0–B8 comparison | #6 (planned) |
| `collect_trace.py` | OTel/Jaeger trace export | #6 (planned) |

Wraps `scripts/kagent/test-a2a-agent.py` — does not implement a second A2A client.
