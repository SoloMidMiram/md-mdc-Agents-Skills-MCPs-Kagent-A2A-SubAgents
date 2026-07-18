# Educational Problem Record: Permissive health overclaim

## Metadata

| Field | Value |
|-------|-------|
| Date and timezone | 2026-07-17 UTC+3:30 |
| Lane | kagent |
| Exercise or phase | phase_5c_truthful_health_profiles |
| Environment | Docker Desktop Kubernetes (`docker-desktop`), namespace `kagent` |
| Relevant versions | health checker with profiles; tools image `0.0.13` |
| Severity | P1 |
| Status | Mitigated |

## Intended Learning and Expected Result

Learners should see that “healthy” depends on the capability under test. Card
lab readiness, direct MCP server success, A2A dispatch, and full agent-mediated
execution must be separable decisions.

## Actual Result

The previous single health script could exit 0 for card-lab conditions while
RemoteMCPServer/tool execution and A2A dispatch remained unproven. That invited
overclaiming “the lab is healthy” as if L4/L6 were included.

## Safety and Containment

- Side effects allowed: read-only kubectl and optional local port-forwarded checks
- Side effects observed: none beyond read-only observation
- Cleanup performed: temporary evidence files under ignored tmp path
- Production/external impact: None

## Minimal Reproduction

```powershell
# Historical: one command, one exit code for mixed capabilities
.\scripts\kagent\check-kagent-health.ps1
# Could pass while A2A task still fails and L6 remains unproven
```

## Layer and Classification

- Zone/layer: kagent education / health gating
- Problem class: Documentation/product semantics drift (permissive aggregate)
- Observed facts: L0–L3 and L5 proven; direct MCP proven as server evidence; L4/L6 not proven
- Assumptions still unverified: positive A2A response shape, evidence freshness
  and target identity, source-path validity, and task-to-tool-trace correlation

## Root Cause

A single aggregate health exit code collapsed distinct capability gates into one
pass/fail, so learners could treat card-lab success as broader execution health.

## Resolution or Workaround

Introduce explicit profiles (`CardLab`, `DirectMcpServer`, `A2ADispatch`,
`FullMcpExecution`) with structured gates, exit codes, and non-claims.
Implementation: `scripts/kagent/KagentHealth.psm1` + updated
`check-kagent-health.ps1`. Reference: `docs/reference/kagent-health-profiles.md`.

## Validation

| Check | Result | Evidence |
|-------|--------|----------|
| Minimal reproduction | Pass | Four-profile live matrix in phase 5C evidence |
| Negative/failure case | Pass | A2ADispatch and FullMcpExecution fail truthfully |
| Stable-core regression checks | Pass | Pester 38/38 on module; pytest MCP suite green |
| Security/policy checks | Pass | read-only live checks; no RBAC/Helm changes |
| Cleanup | Pass | ignored tmp evidence path |

## Capability Decision

- Proven: profile semantics; CardLab pass; DirectMcpServer pass; truthful A2A/Full failures
- Not proven: L4; L6
- Previous claim corrected: “namespace healthy” no longer implies dispatch or agent tools
- Promotion limitation: a future positive A2A/Full decision requires provenance
  and correlation review until the evidence schemas and helper output are hardened

## Reflection

- Why was this difficult? Multiple true statements about one cluster conflict if forced into one boolean.
- Which earlier gate should have caught it? Capability matrix L0–L7 already required separate evidence; health tooling had not.
- Learner takeaway: choose the profile that matches the claim you intend to make.
- Promotion: reference doc + runbook + automated tests; not a new AGENTS rule.

## Follow-up Owner

- Canonical roadmap item: phase_5c_truthful_health_profiles
- Files: health module/script, reference, evidence index, roadmap
- Closure condition: negative/current-state overclaim is mitigated; full closure
  additionally requires structured A2A success validation and correlated,
  target-bound evidence before automated L4/L6 promotion

## Current-state addendum

Phase 5D subsequently supplied strict structured A2A evidence and promoted L4.
Phase 5E now recomputes freshness, validates the observed target and normalized
tool arguments, opens and correlates bounded source JSON, recomputes result-name
matching, and derives the A2A/agent-tool gates from one task. This mitigates the
automated positive overclaim paths identified here. L6 remains Not proven
because the retained live Phase 5E task did not produce a correlated tool
observation; deterministic positive fixtures do not promote the capability.
