# kagent Evidence and Status Index

This index is the canonical current-status summary for the local kagent
educational lane. Detailed records remain dated snapshots and must not be edited
to imply capabilities that were not observed.

## Latest Verified Status

Environment observed through 2026-07-17: local Docker Desktop Kubernetes cluster.

| Level | Decision | Evidence |
|-------|----------|----------|
| L0 | Proven | Manifests and helpers in `deploy/` and `scripts/kagent/` |
| L1 | Proven | [phases 0-2](educational-practice-phase-0-2.md) |
| L2 | Proven | [phases 0-2](educational-practice-phase-0-2.md) |
| L3 | Proven | [phases 0-2](educational-practice-phase-0-2.md) and [phase 3](educational-practice-phase-3.md) |
| L4 | Proven | [phase 5d](educational-practice-phase-5d-trustworthy-a2a.md): `message/stream` status-update with non-empty task id |
| L5 | Proven | [phase 4](educational-practice-phase-4.md): target server accepted and tools discovered |
| L6 | Not proven | [phase 5e](educational-practice-phase-5e-agent-mediated-mcp.md): no correlated tool observation for the A2A task (helper exit 1) |
| L7 | Not proven | No fresh-install bootstrap and cleanup evidence |

The phase 5 MCP `initialize` handshake succeeded. The subsequent direct
`tools/call` failed because its session identifier was not reused
([phase 5](educational-practice-phase-5.md)). That failure is corrected and
live-validated in [phase 5b](educational-practice-phase-5b-direct-mcp.md):
**direct MCP tool invocation is proven** as server evidence only. It still
does not substitute for L6.

Helper implemented and deterministic tests complete.
Live direct-MCP tool invocation proven on 2026-07-17 (see phase 5b).

Problem record: [2026-07-17 MCP session reuse](problems/2026-07-17-mcp-session-reuse.md).
Helper: `scripts/kagent/mcp_session_smoke.py`. Tests: `tests/kagent/test_mcp_session_smoke.py`.

## Implemented Corrections

- `task` and `both` now fail when dispatch fails; `probe` remains observational.
- Card validation now requires both `Accepted=True` and `DeploymentReady=True`.
- Pod readiness parsing accepts any complete positive ratio such as `1/1` or `2/2`.
- A real in-cluster MCP runtime backs `kagent-tool-server`, proving L5.
- The runtime safety description now states the actual control: image `0.0.13`
  lacks native `--read-only`, while its Kubernetes service account has read-only RBAC.
- Roadmap, runbook, and onboarding language distinguish historical phase 0-2
  degradation from the current phase 4/5 state.
- Direct MCP session smoke helper implements mandatory initialize →
  `notifications/initialized` → `tools/list` schema discovery → session-reusing
  `tools/call`, with deterministic offline tests and live phase 5b evidence.
- Named health profiles (`CardLab`, `DirectMcpServer`, `A2ADispatch`,
  `FullMcpExecution`) evaluate independent gates; default remains CardLab.
  Live phase 5c: CardLab/DirectMcpServer pass; A2ADispatch/FullMcpExecution fail
  truthfully.
- Phase 5d trustworthy A2A helper: structured JSON, `message/stream` SSE,
  strict response shapes; L4 proven. The fail-closed review rejects any bad
  event in a mixed stream and requires schema/helper/decision/transport/
  protocol/dispatch agreement. Health consumes JSON only. Problem:
  [2026-07-17 A2A dispatch compatibility](problems/2026-07-17-a2a-dispatch-compatibility.md).
- Phase 5e agent-mediated MCP helper: nested schema 1.0 with one-task A2A
  transport/protocol/dispatch agreement, recomputed freshness, observed target
  binding, exact tool/arguments, bounded source-content correlation, and
  recomputed kubectl name matching. `FullMcpExecution` derives both gates from
  the same Phase 5E task. Live attempt failed closed (no tool marker). L4
  remains Proven; L6 Not proven. Problem:
  [2026-07-17 agent MCP correlation](problems/2026-07-17-agent-mcp-correlation.md).
- The quality workflow now defines a separate locked kagent Python job
  (`uv sync --frozen --group dev`, Ruff, and pytest), pins the suite-compatible
  Pester 3.4.0 baseline, and
  explicitly runs the deterministic kagent PowerShell suite. Hosted Quality run
  [30547297255](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/30547297255)
  passed all jobs at commit `3e8ceaf` on 2026-07-30. This proves deterministic
  CI at that revision but does not change any L0-L7 decision.
- Kubernetes manifest validation (`scripts/kubernetes/validate.ps1 -Strict`)
  and Trivy policy scanning (`scripts/security/scan.ps1 -Required`) now fail
  closed when required tools are missing or return nonzero exits. Pinned
  validator versions (kubeconform v0.6.7, kube-linter v0.7.1, Trivy v0.72.0)
  are installed by separate hosted CI jobs. Deterministic Pester tests cover
  missing-tool and simulated-failure paths in
  `tests/kagent/KagentToolingValidation.Tests.ps1`. Those jobs passed in hosted
  Quality run 30547297255 at `3e8ceaf`; this does not change any L0-L7 decision.
- 2026-07-30 CRD exit-3: `check-kagent-health.ps1` now exits 3 when
  RemoteMCPServer CRD is absent for `DirectMcpServer`, `A2ADispatch`, or
  `FullMcpExecution`. Covered by child-process stubs in
  `KagentToolingValidation.Tests.ps1`.
- 2026-07-30 SSE coalescing: `parse_sse_jsonrpc_events` in
  `test-a2a-agent.py` now joins multi-line `data:` fields before JSON
  decoding. Covered by deterministic pytest in `test_a2a_helper.py`.

## Major Open Flaws

| Priority | Flaw | Impact | Recommended closure evidence |
|----------|------|--------|------------------------------|
| P0 | No live correlated agent-mediated MCP result | Core L6 objective remains unproved; deterministic gates cannot promote it | One fresh `agent_mcp_trace.py` exit 0 binding a taskId to `kagent-tool-server` / `k8s_get_resources`, same-task returned names, bounded source proof, and kubectl match |
| P1 | MCP image advertises write tools | RBAC is the only write barrier and tool discovery is misleading | Native read-only image plus retained restrictive RBAC |
| P1 | Hosted validation status must be tied to the exact committed head | A green script run can lack schema/security validation, or a previous workflow run can be carried forward incorrectly | CI installs validators and fails if unavailable; record the exact successful workflow SHA before changing current-status prose |
| P2 | Controller MCP agent discovery is not yet recorded | A custom IDE bridge could be built unnecessarily, or a native endpoint could be assumed without evidence | Record live `initialize` and `tools/list`; if suitable agent tools are present, use that native surface for the Cursor/Codex acceptance phase |
| P2 | Repeated current-state prose remains in older docs | Runtime claims can drift | Replace copied snapshots with links to this index |
| P2 | Empty-param `message/stream` probes still return `-32603` | Probe noise; not an L4 path | Keep probe observational; document pinned MessageSendParams only |
| P2 | Post-correction hosted validation is not yet recorded | Local correction checks do not establish a hosted result for the corrected revision | Record the exact successful workflow run and commit after this correction is pushed |

## Record Index

- [Phases 0-2 evidence](educational-practice-phase-0-2.md)
- [Phases 0-2 review](educational-practice-phase-0-2-review.md)
- [Phase 3 truthful dispatch semantics](educational-practice-phase-3.md)
- [Phase 4A design](educational-practice-phase-4a-design.md)
- [Phase 4 L5 evidence](educational-practice-phase-4.md)
- [Phase 5 L4/L6 attempt](educational-practice-phase-5.md)
- [Phase 5B direct MCP session reuse](educational-practice-phase-5b-direct-mcp.md)
- [Phase 5C truthful health profiles](educational-practice-phase-5c-health-profiles.md)
- [Phase 5D trustworthy A2A dispatch](educational-practice-phase-5d-trustworthy-a2a.md)
- [Phase 5E correlated agent-mediated MCP](educational-practice-phase-5e-agent-mediated-mcp.md)
- [Problem: MCP session reuse](problems/2026-07-17-mcp-session-reuse.md)
- [Problem: health profile overclaim](problems/2026-07-17-health-profile-overclaim.md)
- [Problem: A2A dispatch compatibility](problems/2026-07-17-a2a-dispatch-compatibility.md)
- [Problem: agent MCP correlation](problems/2026-07-17-agent-mcp-correlation.md)

Definitions: [kagent capability matrix](../../docs/reference/kagent-capability-matrix.md).
Health profiles: [kagent health profiles](../../docs/reference/kagent-health-profiles.md).
Roadmap: [kagent educational roadmap](../../docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md).
