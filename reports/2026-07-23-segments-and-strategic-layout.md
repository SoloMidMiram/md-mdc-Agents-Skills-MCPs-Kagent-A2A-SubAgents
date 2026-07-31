# Segments and Strategic Layout — Boundaries and Integration Direction

**Date:** 2026-07-23
**Classification:** Non-authoritative architecture review snapshot
**Primary question:** How should stable, educational, deterministic, and live
work be organized without confusing repository integration with capability
proof?

The design authority is
[`EDUCATIONAL-LANES-ARCHITECTURE.md`](../docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md).
This report interprets the current implementation; it does not replace that
architecture, either roadmap, or the canonical evidence index.

## 1. Direction

The repository should preserve one release-gated stable core and two isolated
educational zones:

```text
                    shared governance and validation
              (constraints, CI, manifest, documentation rules)
                                   |
          +------------------------+------------------------+
          |                        |                        |
          v                        v                        v
   +-------------+        +----------------+       +----------------+
   | Stable core | <----- | Playwright     |       | kagent         |
   | contracts   |        | education      |       | education      |
   +-------------+        +----------------+       +----------------+
          ^                                                |
          +------------------------------------------------+
                 consumes stable contracts only

Playwright education -X-> kagent implementation details
kagent education     -X-> Playwright implementation details
stable core          -X-> live learner/browser/cluster state
```

Shared governance is not a fourth runtime zone. It spans all three zones and
enforces ownership, validation, and promotion rules.

The strategic direction is:

1. keep the stable host path independently releasable;
2. execute deterministic educational tests in CI without requiring live learner
   state;
3. keep live capability promotion evidence-based and fail-closed;
4. promote a lab utility into stable code only after its interface, side
   effects, tests, security, ownership, and rollback are reviewed.

## 2. Integration Has Five Distinct Layers

The original reports used “integrated” too broadly. Use these layers instead:

| Layer | Question | Evidence |
|-------|----------|----------|
| Artifact | Does the code, manifest, test, or document exist in the owned location? | Repository tree and `REPO_MANIFEST.yaml` |
| Deterministic | Can behavior be evaluated without a browser, cluster, secret, or learner profile? | Offline tests and fixtures |
| Hosted | Does CI execute the deterministic contract on a clean runner? | Required GitHub checks |
| Live | Did the expected external system behavior occur in a named environment? | Dated sanitized evidence |
| Promotion | Is the result sufficient for a canonical capability or stable-interface claim? | Capability matrix or promotion review |

A surface can be repository-integrated but not CI-integrated, or CI-integrated
but not live-proven. That is the current kagent situation.

## 3. Zone Layout and Current State

| Zone | Owned responsibilities | Artifact state | Deterministic state | Hosted state | Live state |
|------|------------------------|----------------|---------------------|--------------|------------|
| Stable core | Agent contracts, host registration, install/verify/rollback, release Quality | Implemented and mapped | 85-case evaluation (80 pass, 5 skip) | Green after PR #2 | Laptop-stable behavior proven; next tag pending |
| Playwright education | Browser exercises, local/remote runtime learning, cleanup and evidence | Runbooks, server scaffold, datasets exist | Partial; stable host tests must not be mistaken for lane coverage | No dedicated lane job | Environment-specific exercises exist |
| kagent education | Kubernetes, A2A, MCP discovery, health profiles, correlation evidence | Phase 0–5E implementation exists in PR #1 | 111 Python and 64 health tests pass on current local branch | Static PowerShell analysis only; behavioral suites absent | L0–L5 Proven; L6/L7 Not proven |
| Shared governance | Constraints, documentation placement, manifest, CI, promotion workflow | Contracts exist | Mostly manual audits | Partial; no manifest or dependency-boundary gate | Not a live capability |

## 4. Dependency and Boundary Rules

| Rule | Current enforcement | Gap | Correct control |
|------|---------------------|-----|-----------------|
| Stable tests cannot depend on live learner state | Clean-runner ConfigRoot evaluation now passes | Continue watching new stable tests | Keep fixtures/temp workspaces and clean-runner CI |
| Educational lanes may consume stable contracts | Documented architecture | No automated dependency check | Static path/import boundary test |
| Educational lanes must not consume each other’s internals | Documented only | Cross-lane imports could be introduced unnoticed | Explicit forbidden-import/path rules |
| Every canonical artifact has one owner | Documentation guide and manifest | Manifest is manually audited | Manifest schema, allowed values, existence, duplicate, and authority checks |
| Generated output does not enter source/config paths | Documented; ignores exist for known results | New result locations can drift | Ignore check plus generated-path audit |
| Live state cannot become a stable test oracle | Architecture rule | Review-dependent | CI tests must reject learner evidence and cluster dependencies |

Manifest validation and dependency-boundary validation are different controls.
Checking that a path exists does not prove that stable code avoids importing
`scripts/kagent/`.

## 5. kagent Capability Track

The canonical L0–L7 definitions are maintained in
[`kagent-capability-matrix.md`](../docs/reference/kagent-capability-matrix.md).

| Level | Current decision | What proves it | Current strategic meaning |
|-------|------------------|----------------|---------------------------|
| L0 | Proven | Repository manifests and helpers | Artifacts exist |
| L1 | Proven | Control-plane observations | Cluster control plane was available |
| L2 | Proven | Accepted/ready agent | Reconciliation worked |
| L3 | Proven | Validated card/details | Agent metadata was observable |
| L4 | Proven | Phase 5D `message/stream` task/status evidence | A2A dispatch crossed the boundary |
| L5 | Proven | Accepted RemoteMCPServer and discovered tools | Controller reached the MCP endpoint |
| L6 | Not proven | Missing same-task tool/result/kubectl correlation | Agent-mediated tool execution remains the primary capability target |
| L7 | Not proven | No fresh setup-to-cleanup replay | Workshop repeatability remains unproved |

Levels are independent evidence gates. Work on bootstrap, cleanup, CI, and
documentation can proceed while L6 is unresolved. However, a workshop that
claims the full agent-mediated path cannot be promoted without qualifying L6
evidence.

## 6. Keep the Two Phase Systems Explicit

The repository intentionally has two planning views:

| Planning view | Canonical owner | Meaning |
|---------------|-----------------|---------|
| Educational Phase 0–5E | `KAGENT-EDUCATIONAL-ROADMAP.md` | Learner sequence and dated educational evidence |
| Engineering Phase 0–4 | `IMPLEMENTED-STATE-AND-ROADMAP.md` | Repository stabilization and implementation work |

Do not write an unqualified “Phase 2” in new cross-cutting documents. Say
“educational Phase 5E” or “engineering Phase 2” so readers do not infer a false
ordering between the two views.

For this report, the engineering phases are expressed as workstreams:

- Publication and release truthfulness;
- deterministic integration;
- live capability promotion;
- hardening and repeatability.

## 7. Concerns Against the Correct Integration Layer

| ID | Concern | Missing layer | Priority | Practical closure |
|----|---------|---------------|----------|-------------------|
| B1 | Two local behavior fixes are not in PR #1 | Publication | P0 | Push to PR #1 or publish immediately on a follow-up branch |
| B2 | L6 lacks one correlated live success | Live/promotion | P0 | Fresh `agent_mcp_trace.py` exit 0 with same-task output and kubectl match |
| B3 | kagent behavioral tests are absent from CI | Hosted | P1 | Dedicated cluster-free Ruff/pytest/health job |
| B4 | Oversized source capture becomes invalid JSON | Deterministic/promotion | P1 | Pre-bound fields, serialize valid JSON, add truncation metadata and regression test |
| B5 | K8s and security validators skip or cannot fail | Hosted/security | P1 | Pin tools, define policy, fail closed, prove invocation |
| B6 | MCP discovery exposes write-capable tools | Runtime defense | P1 | Native read-only tool image plus restrictive RBAC |
| B7 | Manifest and lane boundaries are manual | Governance | P1 | Separate manifest validator and dependency-boundary test |
| B8 | Health tests are tied to Pester 3.4 | Maintainability | P2 | Assertion-preserving migration to current Pester |
| B9 | Current-state prose drifts across summaries | Documentation | P2 | Replace copied claims with canonical links |
| B10 | Repeatable installation depends on one known local environment | Live/repeatability | P2 until L6 | Specify supported bootstrap target and later add an alternative-cluster note |

Evidence retention and tag namespaces are governance candidates, not established
defects. Do not add arbitrary “keep the last N phases” deletion rules: dated
evidence records are historical observations and must not be rewritten to
strengthen later claims.

## 8. Decisions Already in Force

| Decision | Authority | Consequence |
|----------|-----------|-------------|
| Stable core plus two educational zones | Educational-lanes architecture and 2026-07-17 decision record | Labs cannot introduce live assumptions into stable contracts |
| Dependencies point inward to stable contracts | Educational-lanes architecture | Cross-lane implementation dependencies require architecture review |
| `uv` and Ruff own Python environment/linting | `pyproject.toml` and 2026-06-24 decision | Python CI should use the locked environment |
| kubeconform, kube-linter, and Trivy are selected tools | 2026-06-24 decision | Integration remains incomplete until CI installs and enforces them |
| L0–L7 are independent evidence gates | Capability matrix | Readiness, direct MCP, and L5 cannot be promoted as L6 |
| Live state is evidence, not configuration or a test oracle | Educational-lanes architecture | Hosted deterministic tests must not require a cluster |
| `laptop-stable-v*` identifies stable releases | Existing tag and acceptance plan | `v0.1.1` requires a green release-SHA run before tagging |

The following are decision candidates, not yet architecture decisions:

- exact kagent CI job structure and Pester migration timing;
- whether validator findings are all blocking or split into blocking/advisory
  classes;
- the supported L7 bootstrap environment;
- a long-term evidence archival policy.

Record them in `.project-ai/memory/architecture-decisions.md` only after they
are accepted and durable.

## 9. Workstreams and Parallelism

### Workstream A — Publication

1. Decide the destination of `d5c6e29` and `3e22c46`.
2. Push the intended PR head.
3. Wait for hosted Quality.
4. Merge with **L4 Proven; L6 Not proven** unchanged.

### Workstream B — Deterministic integration

1. Add cluster-free Python/Ruff execution to CI.
2. Pin Pester 3.4 temporarily or migrate the health suite.
3. Add manifest validation.
4. Add dependency-boundary validation.

This can proceed independently of live L6.

### Workstream C — Live capability

1. Correct valid bounded source capture.
2. Re-run the Phase 5E live task against the expected target.
3. Promote L6 only on a fresh exit 0 with complete correlation.
4. Preserve failure evidence truthfully otherwise.

### Workstream D — Hardening and repeatability

1. Enforce Kubernetes and security validators.
2. Replace the tool runtime with a native read-only surface.
3. Build the documented bootstrap and cleanup path.
4. Prove L7 on a fresh supported environment.

Implementation can overlap with Workstream C. Capability promotion cannot
borrow evidence from another workstream.

## 10. Recommended Order

| Horizon | Action | Why now | Completion signal |
|---------|--------|---------|-------------------|
| Immediate | Resolve and publish the two local fixes | Prevent stranded work and ambiguous PR state | Remote branch contains intended commits |
| Immediate | Merge PR #1 after checks | Land the reviewed Phase 5B–5E foundation | Clean merge; canonical L6 non-claim retained |
| Next | Fix JSON-safe bounded evidence | Remove a deterministic blocker to a real L6 success | Oversized capture parses and correlates |
| Next | Add deterministic kagent CI | Make behavior regressions visible before merge | Hosted Python/Ruff and health checks |
| Next | Attempt fresh L6 | Close the primary capability gap | Qualifying exit 0 or truthful retained failure |
| Then | Enforce validators and read-only tools | Strengthen integration and defense-in-depth | Required tools run and fail correctly |
| Then | Prove repeatable bootstrap | Complete workshop maturity | Fresh setup, target, cleanup, evidence |

## 11. Ownership Routing

This report must not accumulate an independent backlog. Route accepted changes:

| Accepted change | Canonical destination |
|-----------------|-----------------------|
| L4/L6/L7 status or ranked kagent flaw | `evidence/kagent/README.md` |
| Educational exercise order or gate | `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md` |
| Repository implementation priority | `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md` |
| Stable boundary change | `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md` plus a durable decision |
| Command, recovery, or cleanup change | Applicable runbook |
| Canonical file ownership | `REPO_MANIFEST.yaml` |

If this report is retained, keep it as a dated, non-authoritative review
snapshot. Do not list it as a canonical roadmap or status authority.

## 12. Architecture Health

| Property | Assessment | Reason |
|----------|------------|--------|
| Stable/education ownership | Healthy | Three-zone contract and promotion flow are explicit |
| Stable clean-runner CI | Healthy | PR #2 removed real-profile coupling; hosted Quality is green |
| kagent deterministic quality | Locally strong, hosted incomplete | 111 Python and 64 health tests pass but are not executed in CI |
| Live capability truthfulness | Healthy | L6 failure remains Not proven; direct MCP is not overclaimed |
| Boundary automation | Incomplete | Manifest and cross-lane dependency rules are manual |
| Evidence production | Needs correction | Serialized-text truncation can invalidate source JSON |
| Validator/security enforcement | Incomplete | Missing tools skip and Trivy cannot fail the gate |
| Repeatability | Not proven | L7 lacks fresh setup and cleanup evidence |

The architecture direction is sound. The next maturity gain comes from
connecting existing deterministic contracts to hosted enforcement, while
keeping live capability promotion separate and evidence-driven.
