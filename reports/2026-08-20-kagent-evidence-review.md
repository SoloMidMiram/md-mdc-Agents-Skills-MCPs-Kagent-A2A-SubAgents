# kagent A2A Slice — Evidence-Based Repository Review

**Observed:** 2026-08-20, UTC  
**Classification:** Non-authoritative review snapshot  
**Scope:** Current worktree on `edu/kagent-a2a-role-examples`; no live cluster,
production, staging, push, or commit operation was performed.

This report organizes the current A2A educational slice and verifies what can be
proved from repository artifacts and available local checks. The canonical
capability decisions remain in [`evidence/kagent/README.md`](../evidence/kagent/README.md);
the machine-readable review is [`2026-08-20-kagent-capability-review.json`](2026-08-20-kagent-capability-review.json).

## Executive verdict

The E1–E2 slice is artifact-complete enough for offline review: three sample
manifests, a shared experiment harness, role contracts, deterministic tests, a
runbook, and manifest ownership are present. It is not live-capability complete.

The only dated E1/E2 smoke summary reports accepted task IDs followed by
DeepSeek DNS/egress failures. Therefore E1 and E2 remain **Not proven**. No
capability promotion is justified, and the canonical status is unchanged:

| Track | Proven | Not proven | Blocked | Not attempted |
|---|---|---|---|---|
| kagent L0–L7 | L0–L5 | L6, L7 | — | — |
| Native IDE I0–I5 | I0–I2 | I4 | I3 | I5 |
| Educational examples | — | E1, E2 | live DeepSeek DNS/egress | E3–E5 |

An accepted A2A task is not a successful structured agent result; a manifest,
contract test, or health check is not live capability evidence.

## Verified repository state

The worktree was already dirty when this review began. `HEAD` is `543f83d`
(`docs(kagent): sync current-state docs to I3 tool-discovery blocker`). The
checkout contains broad tracked modifications, many of which are
line-ending-only; after ignoring EOL whitespace, 17 tracked files contain
substantive changes, alongside the new A2A tree. Those pre-existing changes are
preserved and are not silently treated as this review’s authored baseline.

The substantive slice is organized as follows:

| Concern | Canonical owner | Current state |
|---|---|---|
| Direction and lane boundaries | `docs/north-star.md`, `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md` | A2A-first direction documented; Cursor I3/L6/I4 kept separate |
| E1–E5 procedures | `docs/runbooks/kagent-a2a-examples.md` | E1/E2 runnable procedure; E3–E5 explicitly planned/deferred |
| Sample manifests | `deploy/samples/kagent-a2a/` | Planner, reviewer, supervisor manifests present; docs/capstone placeholders |
| Experiment code | `scripts/kagent/experiments/` | Shared transport wrapper, contracts, and sanitizer present |
| Deterministic tests | `tests/kagent/experiments/` | Contract, mapping, and record-builder coverage present |
| Dated results | `evidence/kagent/experiments/README.md` | Blocked smoke summary; no positive E1/E2 record |
| Path ownership | `REPO_MANIFEST.yaml` | New canonical paths mapped |

## Checks actually executed

| Check | Result | Evidence/interpretation |
|---|---|---|
| Python AST parse and compile of new code/tests | **PASS** | Four files parsed and compiled with `/usr/bin/python3.14` |
| Offline contract smoke | **PASS** | Planner, reviewer, supervisor acceptance/rejection paths and record sanitization exercised |
| YAML parse of three new Agent manifests | **PASS** | PyYAML parsed all three documents and required top-level fields were present |
| New-file manifest coverage | **PASS** | All 18 new slice paths matched `REPO_MANIFEST.yaml` entries |
| Markdown links in new slice and touched onboarding docs | **PASS** | Link audit passed after correcting three shallow sample links |
| `uv run ruff check scripts/kagent tests/kagent` | **UNAVAILABLE** | `uv` is not installed in this environment |
| `uv run pytest -q tests/kagent` | **UNAVAILABLE** | `uv` is not installed; the configured Python shims also have unusable CRLF interpreters |
| Bundled PowerShell slice audit | **UNAVAILABLE** | `pwsh` is not installed |
| Live A2A or Kubernetes run | **NOT RUN** | No cluster mutation or external-state operation was authorized or needed |

The local checks establish syntax, parsing, contracts, links, and ownership.
They do not establish pytest/Ruff success, hosted CI success, agent readiness,
provider reachability, A2A task completion, sub-agent hops, or any L6/I4 claim.

## Evidence findings

1. E1 planner-only and E2 supervisor flows are **Not proven**. The dated
   experiment summary records task IDs but DeepSeek HTTP calls failed on cluster
   DNS/egress. The next run must capture exact commands, exit codes, environment
   versions, terminal state, structured artifact, and explicit non-claims.

2. The new harness has appropriate fail-closed intent. It validates role-specific
   JSON contracts, preserves a sanitized controller origin, records cleanup
   commands, and keeps L6/I3/I4/MCP/Codex/Cursor in the non-claims list. These
   are implementation properties, not live results.

3. Existing L6 evidence remains negative. The repository’s prior Phase 5E run
   had no same-task tool marker, tool-derived names, or matched Kubernetes
   result. Direct MCP success and L5 acceptance remain insufficient for L6.

4. Existing I3 evidence remains blocked at Cursor tool discovery. No current
   A2A educational artifact changes that decision; the pivot changes sequencing,
   not capability status.

5. Synchronization defects found during review were corrected: three sample
   links were one directory too shallow, two placeholder READMEs used stale PR
   numbers for the read-only MCP dependency, and two archived redirect links
   pointed at a nonexistent nested directory.

6. The experiment README is a blocked-smoke summary rather than a complete new
   evidence record under the repository contract. Do not use it to promote E1 or
   E2; append a dated, exact-command record after a real run succeeds or fails.

## Commit drafts (not staged or committed)

These are publication units, not claims that hosted GitHub commits or PRs exist.
The worktree index remains empty. Because the checkout contains unrelated and
line-ending-only changes, stage each draft by an explicit path after reviewing
the final diff.

### Draft 1 — implementation slice

`feat(kagent): add bounded A2A role examples and contracts`

Include the planner, reviewer, and supervisor sample manifests and READMEs;
`scripts/kagent/experiments/{README.md,contracts.py,record_experiment.py,run_a2a_example.py}`;
and `tests/kagent/experiments/{README.md,test_a2a_experiments.py}`.

### Draft 2 — canonical synchronization

`docs(kagent): synchronize A2A-first direction and evidence ownership`

Include `docs/north-star.md`, the affected onboarding/architecture/runbook
documents, `evidence/kagent/README.md`, `evidence/kagent/experiments/README.md`,
the corrected sample READMEs, and the corresponding `REPO_MANIFEST.yaml`
entries. Keep historical evidence records untouched.

### Draft 3 — review artifacts

`docs(kagent): add dated evidence review and capability classification`

Include this Markdown report and its JSON review contract. Both are dated,
non-authoritative snapshots; neither replaces the evidence index or roadmap.

### Draft 4 — README last

`docs: refresh README navigation after repository sync`

Include only the final README navigation/status links after Drafts 1–3 are
reviewed. README must link to the north star, E1–E5 runbook, canonical evidence,
and this dated report without copying volatile runtime details.

Do not include the broad line-ending-only worktree changes in these drafts unless
they are deliberately reviewed as a separate normalization change.

## Required next evidence run

When the local cluster/provider path is healthy, execute E1 first and E2 second.
For each run retain the exact command, environment and component versions,
task id, terminal state, structured artifact, exit code, cleanup result, and
explicit non-claims. For E2, retain bounded proof of both planner and reviewer
sub-agent hops. A DNS failure should be recorded as **Blocked** for the run, not
as a partial pass.

No changes to the canonical L0–L7 or I0–I5 decisions are warranted from this
review.
