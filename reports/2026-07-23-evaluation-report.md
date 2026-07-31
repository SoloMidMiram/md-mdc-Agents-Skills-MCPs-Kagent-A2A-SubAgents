# Evaluation Report — Verified Integration State and Decisions

**Date:** 2026-07-23
**Classification:** Non-authoritative review snapshot
**Primary question:** What is integrated now, what remains unproved, and what
must happen before publication or capability promotion?

This report is decision support, not a second roadmap or status ledger. Current
kagent capability decisions remain in
[`evidence/kagent/README.md`](../evidence/kagent/README.md); phase order remains
in the
[`KAGENT-EDUCATIONAL-ROADMAP.md`](../docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md);
repository engineering work remains in
[`IMPLEMENTED-STATE-AND-ROADMAP.md`](../docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md).

## 1. Executive Decision

PR #1 is not blocked by the absence of live L6 evidence because the PR
truthfully claims **L4 Proven; L6 Not proven**. It is also not currently blocked
by the stable Quality workflow: its six-commit remote head is mergeable and has
two successful hosted checks.

There is one publication decision before merge:

- the local branch has two additional fix commits that are not on PR #1;
- either push those commits and wait for the hosted checks again, or move them
  to a follow-up branch before merging PR #1.

Adding deterministic kagent tests to hosted CI is important integration work,
but it should be a focused follow-up rather than an unbounded expansion of PR
#1. The invalid source-capture truncation must be corrected before another L6
promotion attempt because it can produce evidence that the consumer cannot
parse.

## 2. Verified Baselines

| Scope | Commit/state | Verified result | Interpretation |
|-------|--------------|-----------------|----------------|
| `main` | `d559ca1`, PR #2 merged | Stable evaluation path fixed; Gate A3 closed | Clean-runner structural validation is no longer coupled to a user profile |
| PR #1 remote | `f9524b7`, six commits | Open, mergeable, clean merge state, two hosted `Repository Evaluation` checks passed | Stable-core Quality gates pass with the Phase 5B–5E changes present |
| Local checkout | `3e22c46`, eight commits ahead of `origin/main` | 111 Python tests passed; 64 Pester 3.4 health tests passed; Ruff clean | Two additional fixes are validated locally but are not in PR #1 |
| Live kagent evidence | Observed through 2026-07-17 | L0–L5 Proven; L6 and L7 Not proven | Deterministic gates exist, but no fresh live correlated L6 result exists |
| These reports | Untracked `reports/` files | Not in `REPO_MANIFEST.yaml` | Review artifacts only; they must not become canonical status owners |

The two local-only commits are:

| Commit | Files affected | Review result |
|--------|----------------|---------------|
| `d5c6e29` | A2A helper and tests | Human card output now renders allowlisted card metadata; deterministic tests pass |
| `3e22c46` | Direct MCP helper, tests, reference, and runbook | A successful main operation now fails when cleanup fails; HTTP 405 remains an explicit compatibility outcome |

## 3. Integration State by Surface

“Integrated” is split into four different questions. Repository presence,
deterministic validation, hosted CI, and live capability evidence are not
interchangeable.

| Surface | Repository integration | Deterministic validation | Hosted CI | Live/capability state | Next gate |
|---------|------------------------|--------------------------|-----------|-----------------------|-----------|
| Stable Playwright host install, verify, rollback | On `main` | 80 passed / 5 skipped in the evaluation suite | Yes | Laptop-stable behavior proven; `v0.1.1` tag still pending | Record green release-SHA run, then tag |
| kagent PowerShell collection and health profiles | In PR #1 | 64/64 Pester 3.4 tests | Static PSScriptAnalyzer only; health tests are not executed | CardLab and evidence-backed profiles retain their documented outcomes | Add deterministic health job or migrate suite to current Pester |
| Direct MCP lifecycle | In PR #1 plus local cleanup fix | Python tests included in the current 111/111 total | Not executed | Direct MCP server evidence proven; not L4 or L6 | Publish cleanup fix; add Python CI |
| Trustworthy A2A dispatch | In PR #1 plus local human-output fix | Python tests included in 111/111 | Not executed | L4 Proven from Phase 5D | Publish local fix; keep response-shape gates fail-closed |
| Agent-mediated MCP correlation | In PR #1 | Deterministic producer and evaluator tests pass | Not executed | L6 Not proven; retained live attempt exited 1 | Produce valid bounded JSON, then obtain one fresh live exit 0 |
| kagent manifests | In PR #1 | No required schema/lint gate | No kubeconform or kube-linter step | L0/L5 evidence exists for the observed cluster | Install validators and fail when unavailable or invalid |
| Repository manifest and lane boundary | Mapped and documented | Manual audits only | No validator | Organizational contract exists | Add path/schema/duplicate validation and a separate dependency-boundary check |
| Security scan | Script exists | No enforced threshold | Not run | `trivy` absence skips; configured command uses `--exit-code 0` | Define policy and make required scans fail closed |

## 4. Findings and Priorities

### P0 — Capability: L6 remains unproved

The canonical blocker is still one fresh A2A task correlated to
`kagent-tool-server` / `k8s_get_resources`, with tool-derived names returned by
the same task and independently matched to Kubernetes. Direct MCP success, L5
acceptance, or deterministic positive fixtures cannot substitute for that
observation.

Closure evidence:

```text
agent_mcp_trace.py exit 0
same taskId/requestId
server = kagent-tool-server
tool = k8s_get_resources
arguments = pod/kagent
same-task returned resource names
fresh bounded source evidence
kubectl matched = true
```

### P0 — Publication: dispose of the two local-only commits

PR #1 currently ends at `f9524b7`; the local branch ends at `3e22c46`. Merging
without deciding where those fixes belong risks losing or accidentally mixing
reviewed work.

Practical choice:

1. push both fixes to PR #1 because they correct behavior introduced in that
   PR;
2. rerun hosted Quality;
3. retain the recorded local 111/111 Python and 64/64 health results in the PR
   discussion;
4. merge only after the new remote head is green.

If review scope must remain exactly six commits, branch the two fixes from PR
#1 and publish them immediately afterward instead.

### P1 — Deterministic kagent behavior is not executed in CI

The Quality workflow runs the stable 85-case evaluation suite (80 pass and
5 skip on the verified path) and recursively
applies PSScriptAnalyzer to PowerShell, but it does not execute:

- the current 111 Python kagent tests;
- Ruff against the Python kagent implementation;
- the 64 Pester health-profile tests.

This is a behavioral coverage gap, not “zero CI coverage”: stable tests and
PowerShell static analysis already run on every push and pull request.

Recommended follow-up job:

1. install `uv` and use Python 3.12;
2. run `uv sync --frozen --group dev`;
3. run `uv run ruff check scripts/kagent tests/kagent`;
4. run `uv run pytest -q`;
5. run health tests either through a temporary pinned Pester 3.4 job or, more
   sustainably, after migrating the suite to current Pester syntax.

No live cluster belongs in this deterministic job.

### P1 — Source capture truncation can create invalid JSON

[`agent_mcp_trace.py`](../scripts/kagent/agent_mcp_trace.py) currently serializes
the capture and then slices the serialized text:

```python
text = text[:MAX_SOURCE_CHARS] + "\n…truncated…\n"
```

That output is not valid JSON. The FullMcpExecution consumer explicitly opens
`sourceEvidencePath` and rejects malformed JSON, so a sufficiently large
otherwise-valid capture can never pass the L6 gate.

Required correction before the next L6 attempt:

- bound lists and string fields before serialization;
- retain a valid object with `truncated: true`;
- record original and retained counts or lengths;
- add a test that exceeds the limit, parses the file with `json.loads`, and
  verifies the retained correlation fields.

This fails closed today, so it does not create a false L6 claim; it can block a
real positive observation.

### P1 — Kubernetes and security validators are fail-open

[`scripts/kubernetes/validate.ps1`](../scripts/kubernetes/validate.ps1) skips
when kubeconform or kube-linter is unavailable. The Quality workflow does not
install or invoke either validator.

[`scripts/security/scan.ps1`](../scripts/security/scan.ps1) also skips when
Trivy is unavailable and invokes Trivy with `--exit-code 0`, so findings cannot
fail a gate.

Practical integration requires:

- pinned tool installation;
- an explicit required-versus-advisory policy;
- non-zero exit propagation for required schema, lint, secret, or
  misconfiguration findings;
- a CI step that proves the tools actually ran.

### P1 — Native read-only MCP exposure remains unresolved

The current tool image exposes write-capable tools while Kubernetes RBAC is the
write barrier. That is a valid defense, but discovery remains misleading and
defense-in-depth is incomplete. Closure requires a native read-only tool
surface while retaining restrictive RBAC.

### P2 — Pester compatibility debt

The 64 health tests intentionally target Pester 3.4 syntax and fail under
current Pester. This is not a product failure, but it complicates CI and splits
the repository between test frameworks. Migrate in a focused change; do not
weaken assertions merely to change syntax.

### P2 — Documentation drift exists outside these reports

Examples found during this review:

- `GETTING-STARTED.md` already links the educational-lanes architecture, so
  “onboarding does not reference the zones” is no longer an open concern;
- the laptop-stable plan still contains older A2A and Node-version prose even
  though L4 is now proven through `message/stream` and Quality uses Node 24;
- current-state prose should link to the evidence index instead of copying live
  counts.

These are documentation corrections, not capability blockers.

## 5. Merge and Follow-up Checklist

### Required before merging PR #1

- [ ] Decide whether `d5c6e29` and `3e22c46` belong in PR #1 or a follow-up.
- [ ] If pushed, confirm the new PR head and both hosted Quality checks pass.
- [ ] Preserve the canonical claim: **L4 Proven; L6 Not proven**.
- [ ] Confirm no unrelated files or these untracked reports enter the PR.

### Required before the next L6 promotion attempt

- [ ] Make bounded source capture valid JSON.
- [ ] Add oversized-capture regression coverage.
- [ ] Run the correlated live task against the expected context and namespace.
- [ ] Retain the fresh, sanitized source evidence and kubectl comparison.

### Recommended follow-up integration

- [ ] Add a deterministic kagent CI job for Ruff, pytest, and health evaluation.
- [ ] Add fail-closed manifest, Kubernetes, and security validation.
- [ ] Correct stale laptop-stable and onboarding summaries.
- [ ] Record a release-SHA Quality run before tagging `laptop-stable-v0.1.1`.

## 6. Practical Sequence

| Order | Action | Output | Proof |
|------:|--------|--------|-------|
| 1 | Publish or branch the two local fixes | No work stranded locally | PR/branch head contains the intended commits |
| 2 | Merge PR #1 after hosted checks | Phase 5B–5E implementation lands | Clean merge, L6 non-claim retained |
| 3 | Fix valid bounded source capture | Positive L6 evidence can be consumed | Oversized capture parses and correlates |
| 4 | Add deterministic kagent CI | Behavioral regressions become merge-visible | Hosted Ruff, pytest, and health checks |
| 5 | Attempt fresh live L6 | Capability promotion decision | Exit 0 promotes; any other result remains Not proven |
| 6 | Add fail-closed validators and read-only runtime | Stronger integration and security | Tools installed, invoked, and enforced |
| 7 | Build and prove repeatable setup | L7 evidence | Fresh setup, target state, cleanup, dated record |

## 7. Metrics Without Scope Mixing

| Metric | Verified value | Scope |
|--------|----------------|-------|
| Stable evaluation | 80 passed, 5 skipped | Stable Playwright host/evaluation path |
| PR #1 hosted checks | 2 successful | Six-commit remote head `f9524b7` |
| Current local Python | 111 passed | Eight-commit local kagent branch |
| Current local health suite | 64 passed | Pester 3.4 only |
| Current local Ruff | Clean | `scripts/kagent` and `tests/kagent` |
| PR-only commits | 6 | Remote PR head relative to merged `main` |
| Local-only fix commits | 2 | Not yet present in PR #1 |
| Proven kagent levels | L0–L5 | Dated evidence through 2026-07-17 |
| Unproved kagent levels | L6, L7 | No qualifying live evidence |

Do not add these counts together as one “coverage” number: the suites exercise
different contracts and have different execution environments.

## 8. Report Disposition

This file should remain a dated review snapshot. Accepted actions must be moved
to their canonical owners:

- capability status and flaws → `evidence/kagent/README.md`;
- educational phase work → `KAGENT-EDUCATIONAL-ROADMAP.md`;
- repository integration work → `IMPLEMENTED-STATE-AND-ROADMAP.md`;
- durable boundary decisions → `.project-ai/memory/architecture-decisions.md`
  only after an actual decision;
- operational commands → the applicable runbook.

Do not add this report to `REPO_MANIFEST.yaml` as an authoritative status file.
