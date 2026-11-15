# A2A evidence laboratory

Run from the repository root:

```sh
uv run --frozen python -m scripts.kagent.experiments.run_evidence_lab
uv run --frozen python -m pytest -q tests/kagent/experiments/test_evidence_lab.py
```

The lab passes six in-memory observations through the same decision function as the live trace. It makes no network, cluster, model, or MCP calls.

| Scenario | Expected verdict |
| --- | --- |
| Accepted dispatch with no observed tool | L4 only |
| Direct MCP observation without accepted dispatch | Gate failure |
| Different dispatch and tool task IDs | Gate failure |
| Observed tool with no result returned through A2A | Gate failure |
| Returned names differ from the independent cross-check | Gate failure |
| Correlated observations with matching names | Synthetic pass |

L4 establishes acceptance at the A2A dispatch gate. L6 requires correlated evidence of a tool invocation, a result returned through A2A, a matching independent cross-check, and target binding. The synthetic case exercises the verdict logic with fixture data. It cannot establish a live observation. Every result carries `origin: synthetic` and `capabilityPromotion: false`. The lab writes no evidence files. See the [evidence index](../../evidence/kagent/README.md) for verified capability status.
