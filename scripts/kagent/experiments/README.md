# kagent A2A Experiment Harness

Scripts for Lane A education (EDU-01) and Lane B benchmarking (EVAL-01). See
[Project North Star](../../../docs/north-star.md).

| Script | Purpose | Workstream |
|--------|---------|-----------|
| `run_a2a_example.py` | Single-role A2A dispatch with contract validation | EDU-01 |
| `record_experiment.py` | Sanitized evidence JSON writer | EDU-01 |
| `contracts.py` | Planner/reviewer/supervisor JSON contracts | EDU-01 |
| `benchmark_a2a.py` | Baselines B0–B8 comparison | EVAL-01 (planned) |
| `collect_trace.py` | OTel/Jaeger trace export | EVAL-01 (planned) |

Wraps `scripts/kagent/test-a2a-agent.py` — does not implement a second A2A client.
# EVID-01 evidence compatibility

The harness and recorder emit `schemaVersion: "1.1"`. Successful examples now
require a correlated request ID and task ID, a terminal `completed` result,
accepted/ready card flags, and a complete role artifact. A summary-only supervisor
does not qualify. `--skip-contract` is diagnostic and cannot pass an example.

The recorder validates source observations before computing acceptance. Its
`observation` retains source time, IDs, status, and claimed pass; `acceptance`
describes the local validation decision, not independently authenticated live
proof. Genuine failures remain recordable with `pass: false`, a reason, target,
observation time, and duration, even when no task was created.

Existing version 1.0 evidence remains historical and is never rewritten.
Version 1.0 inputs may be recorded only if they include the required proof;
incomplete historical success records fail explicitly rather than receiving
fabricated defaults. Artifact data is retained in sanitized form for review.

Only registered `e1-planner`, `phase2-reviewer`, and `e2-supervisor` identifiers
are accepted, paired with their corresponding agent. Output names include date,
example, and a random suffix; exclusive creation prevents accidental overwrite,
including a suffix collision. Invalid input exits 2 before creating a record.
Recording a valid failure exits 0: this means recording succeeded, not the run.

Credential-labelled fields and text are redacted recursively; URLs retain only
their origin. Do not supply secrets: this hygiene is not a general secret scanner
and cannot recognize arbitrary unlabeled secret values. Raw prompts and transport
bodies are not retained by the recorder. L6, I3, I4, and L7 remain non-claims.
