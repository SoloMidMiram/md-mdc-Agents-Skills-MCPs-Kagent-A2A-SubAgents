# CTX-01: Offline source-grounded context packets

This first interface automatically assembles LAB-01's manually selected evidence.
It reads local Git content at an explicit commit, verifies source hashes and line
ranges, and emits a deterministic JSON packet. It does not discover relevant
files or evaluate whether a human-authored claim is true.

Tracking: [CTX-01 #12](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues/12).
Baseline acceptance remains owned by [RECON-01 #11](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/issues/11).
The [manual LAB-01 result](../../evidence/labs/lab-01/2026-10-25/README.md)
is the first fixture, reviewed in PR #10. Context7/CTX-02, model execution,
orchestration and EVAL-01 remain proposed.

## Replay

From the repository root, with Git, uv and Python >=3.12:

```powershell
uv run --frozen --group dev python scripts/context/build_packet.py `
  --repo . --spec tests/context/fixtures/lab-01.json --output ../lab01-context.json
uv run --frozen --group dev python -m pytest -q tests/context
```

Use a new output filename on each run. Without `--output`, JSON is written to
stdout. Exit 0 means the packet passed source/reference checks; exit 2 means
rejection, with a diagnostic on stderr. Existing outputs are never overwritten.
No output file is opened until all source and claim-reference validation passes.
No network, provider, Context7, A2A, MCP or Kubernetes request is made by the builder.
uv may install development dependencies when preparing its environment.

## Input contract, schema_version 1.0

See the runnable [LAB-01 specification](../../tests/context/fixtures/lab-01.json).

| Field | Meaning |
|---|---|
| `source_revision` | Full lowercase 40-character local Git commit SHA; moving refs are rejected |
| `task` | Non-empty task statement |
| `sources` | 1–100 entries: unique `id`, canonical repository-relative `path`, inclusive one-based `start_line`/`end_line`, expected full Git-blob `sha256` |
| `claims` | Up to 100 declarations, each with `statement`, `kind` (`recorded` or `inference`) and non-empty `source_ids` resolving to selected evidence |
| `unknowns` | Up to 100 non-empty strings describing missing observations |
| `exclusions` | Up to 100 non-empty strings bounding authorized actions and conclusions |

All fields above plus `schema_version` are required. Source files must be regular
tracked UTF-8 blobs, not symlinks/submodules/directories. Source changes staged or
unstaged relative to the pinned commit are rejected; unrelated working files and
later commits are allowed. Missing files, changed hashes, invalid line ranges,
escaping paths, wildcard/magic pathspecs and dangling source IDs are rejected.
Git blob bytes define the hash; checkout CRLF conversion does not change it.
Refreshing a changed source requires deliberate review of both hash and line spans.

The input JSON and total full source-blob bytes each have a 2 MB limit. Git commands
have a 30-second timeout. This is a local trusted-repository tool; source excerpts
remain untrusted content for any consuming model and are not execution instructions.

## Output contract, schema_version 1.0

The packet contains `source_revision`, `task`, `evidence` (source IDs, paths,
inclusive line spans, hashes and exact line excerpts), `claims`, `unknowns`,
`exclusions` and `validation_scope`. Excerpt lines use LF without a trailing
newline; hashes cover the full original Git blob. The output deliberately has
no current timestamp, absolute machine path, live status, generated conclusion
or evaluator answer. Repeated assembly from the same inputs is byte deterministic.

Source hashes and resolvable claim references are provenance checks. A declared
`recorded` claim may still misrepresent its cited excerpt; semantic evaluation
remains a separate agent/evaluator responsibility. Passing this builder does not
promote L6 or assert fresh L4 operation.

## Validation and next experiment

Tests cover exact excerpt output, determinism, dirty/missing/symlink sources,
hash drift, invalid ranges, path escape, duplicate/dangling IDs, byte limits,
revision pinning, output preservation and replay of all six real LAB-01 sources.
The normal pytest CI job discovers these tests; Ruff also covers the new paths.

EVAL-01 should compare manual and generated packets using this same source set,
task, model/settings, budget and evaluator rubric. Keep subject/evaluator answers
and scoring artifacts out of both model inputs, retain failures, and account for
preparation costs. This implementation records no coding-improvement outcome.
