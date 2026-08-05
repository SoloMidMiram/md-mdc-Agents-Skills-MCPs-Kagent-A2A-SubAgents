# kagent Evidence and Status Index

This index is the canonical current-status summary for the local kagent
educational lane. Detailed records remain dated snapshots and must not be edited
to imply capabilities that were not observed.

## Latest Verified Status

Environment observed through 2026-08-04: local Docker Desktop Kubernetes cluster,
including the Phase 6E strict-preflight observation.

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

## Native IDE-Federation Status

The native controller MCP surface is tracked independently from L0-L7 so that
agent discovery cannot be mistaken for agent-mediated Kubernetes execution.

| Level | Decision | Evidence |
|-------|----------|----------|
| I0 | Proven | [phase 6](educational-practice-phase-6-native-mcp-federation.md): controller `/mcp` initialized |
| I1 | Proven | [phase 6](educational-practice-phase-6-native-mcp-federation.md): `tools/list` returned the pinned agent tools |
| I2 | Proven | [phase 6](educational-practice-phase-6-native-mcp-federation.md): `list_agents` returned `kagent/k8s-a2a-agent` |
| I3 | Blocked | [phase 6](educational-practice-phase-6-native-mcp-federation.md) and [phase 6b–6d closure](educational-practice-phase-6b-6d-closure.md) (2026-08-02 singleton inventory; 2026-08-03 DeepSeek Flash qualification; 2026-08-04 Phase 6E: task/expected contract corrected and Candidate B strict preflight exited 0 with `strictPreflightQualified=true`). The remaining I3 evidence is a real Cursor trace proving second-call context forwarding; the required Cursor MCP tool-input arguments were not observable in the non-UI acceptance environment. Python helper success alone is insufficient. |
| I4 | Not proven | No same-invocation controller, A2A task, tool result, and `kubectl` correlation. The current `agent_mcp_trace.py` creates its own direct A2A task, so a separate helper run cannot prove that an IDE invocation caused that task. |
| I5 | Not attempted | No fresh setup, restart, both-client acceptance, and cleanup record |

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
  Pester 3.4.0 baseline, and explicitly runs the deterministic kagent
  PowerShell suite. Post-correction Hosted Quality run
  [30621076867](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/30621076867)
  passed all jobs at commit `f18b906` on 2026-07-31. This proves deterministic
  CI at that revision but does not change any L0-L7 decision.
- Kubernetes manifest validation (`scripts/kubernetes/validate.ps1 -Strict`)
  and Trivy policy scanning (`scripts/security/scan.ps1 -Required`) now fail
  closed when required tools are missing or return nonzero exits. Pinned
  validator versions (kubeconform v0.6.7, kube-linter v0.7.1, Trivy v0.72.0)
  are installed by separate hosted CI jobs. Deterministic Pester tests cover
  missing-tool and simulated-failure paths in
  `tests/kagent/KagentToolingValidation.Tests.ps1`. Those jobs passed in hosted
  Quality run 30621076867 at `f18b906`; this does not change any L0-L7 decision.
- 2026-07-30 CRD exit-3: `check-kagent-health.ps1` now exits 3 when
  RemoteMCPServer CRD is absent for `DirectMcpServer`, `A2ADispatch`, or
  `FullMcpExecution`. Covered by child-process stubs in
  `KagentToolingValidation.Tests.ps1`.
- 2026-07-30 SSE coalescing: `parse_sse_jsonrpc_events` in
  `test-a2a-agent.py` now joins multi-line `data:` fields before JSON
  decoding. Covered by deterministic pytest in `test_a2a_helper.py`.
- 2026-07-31 Windows runner CI repair: `bc1ce58` registers PSGallery with
  `Register-PSRepository -Default` when it is absent before trusting it. This
  restores Pester 3.4.0/5.7.1 installation on the Windows Server 2025 runner.
  Hosted Quality run
  [30621076867](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/30621076867)
  passed all jobs at `f18b906`; follow-up Quality run
  [30621919672](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/runs/30621919672)
  passed all jobs at the exact pre-merge head `94031ff` on 2026-07-31. That
  revision is now part of merged PR #1 and remains historical CI context, not
  an active merge gate; it does not change any L0-L7 decision.
- Phase 6 native federation now has a deterministic Streamable HTTP helper for
  the pinned controller contract and project-scoped Cursor/Codex configurations.
  The live controller exposes `list_agents` and `invoke_agent`; I0-I2 are
  proven. The dated I3-Cursor decision is maintained in the Native
  IDE-Federation Status table above. Native MCP is the preferred client seam,
  so a custom A2A-to-MCP gateway remains deferred.
- 2026-07-31 correction cycle: MCP-session reuse is named separately from
  agent-context continuation; strict approved-agent inventory is available for
  IDE acceptance; Codex `tool_timeout_sec` is 90 with startup still 30; Cursor
  I3 acceptance is documented as a UI gate because local CLI help did not expose
  a verified MCP invoke command. I3 remains Blocked.
- 2026-07-31 Phase 6B–6D: hybrid leak detection; exact
  `--expected-inventory` profile; IDE-safe Ollama ModelConfig manifests; runbook
  Minimal-profile + Cursor tool-trace requirements. Live closure attempt
  recorded in [phase 6b–6d](educational-practice-phase-6b-6d-closure.md); I3
  remains Blocked (draft stay).
- 2026-08-02 Phase 6B retry: the local Docker Desktop demo Agent CRs were
  deliberately removed and only reviewed resources reapplied, producing the
  exact singleton `kagent/k8s-a2a-agent` inventory. The pinned Ollama model
  pull still failed at registry DNS before provider qualification; the agent
  remained on `default-model-config`, no Cursor trace was attempted, and I3
  remains Blocked. Phase 7 was not started.
- 2026-08-03 DeepSeek fallback: a stdlib-only, redacting provider qualifier
  selected `deepseek-v4-flash` after bounded no-tool and dummy function-schema
  HTTP 200 checks. Its target-only ModelConfig and Agent patch reconciled, but
  the controller preflight did not qualify before rollback and no Cursor trace
  was attempted. I3 remains Blocked; no Kubernetes tool was requested.
- 2026-08-04 Phase 6D: `--observe-only` controller preflight shipped with
  `strictPreflightQualified` markers and deterministic tests. Live DeepSeek
  observe-only passed under the singleton inventory; the immediate strict
  retry failed closed on a non-deterministic echoed task reply. Agent rolled
  back to `default-model-config`. No Cursor trace. I3 remains Blocked.
- 2026-08-04 Phase 6E: fixed contradictory task/expected defaults; Candidate A
  DeepSeek-only strict failed on continuation prepend; Candidate B
  target-only I3 `systemMessage` patch produced strict exit 0. Cursor UI
  `context_id` forward trace still not captured. Rolled back to default
  profile. I3 remains Blocked; PR #3 stays draft.

## Major Open Flaws

| Priority | Flaw | Impact | Recommended closure evidence |
|----------|------|--------|------------------------------|
| P0 | No live correlated agent-mediated MCP result | Core L6 objective remains unproved; deterministic gates cannot promote it | One fresh `agent_mcp_trace.py` exit 0 binding a taskId to `kagent-tool-server` / `k8s_get_resources`, same-task returned names, bounded source proof, and kubectl match |
| P0 | No fail-closed IDE-to-A2A join for I4 | `agent_mcp_trace.py` owns a new direct A2A dispatch; running it beside Cursor would create separate evidence and cannot prove the IDE caused the qualifying task | After I3 and L6 prerequisites, add an external-invocation capture/ingestion path that dispatches no second task and binds the Cursor MCP request to the same A2A taskId, tool marker, returned names, and kubectl match; block I4 if no stable join key is observable |
| P1 | MCP image advertises write tools | RBAC is the only write barrier and tool discovery is misleading | Native read-only image plus retained restrictive RBAC |
| P1 | I3-Cursor blocked: Candidate B strict controller preflight qualifies, but no Cursor tool-trace proves second-call `context_id` forwarding | Cursor cannot complete the IDE-safe acceptance | Re-apply Candidate B profile, run the Cursor UI sequence with sanitized `<context-id-A>` evidence that the second `invoke_agent` forwarded `context_id`; if arguments cannot be observed, record `I3-Cursor: Blocked — second-call Cursor MCP tool-input arguments were not observable in the acceptance environment` ([6b–6d](educational-practice-phase-6b-6d-closure.md)) |
| P2 | Repeated current-state prose remains in older docs | Runtime claims can drift | Replace copied snapshots with links to this index |
| P2 | Empty-param `message/stream` probes still return `-32603` | Probe noise; not an L4 path | Keep probe observational; document pinned MessageSendParams only |

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
- [Phase 6 native MCP federation](educational-practice-phase-6-native-mcp-federation.md)
- [Phase 6B–6D closure attempt](educational-practice-phase-6b-6d-closure.md)
- [Problem: MCP session reuse](problems/2026-07-17-mcp-session-reuse.md)
- [Problem: health profile overclaim](problems/2026-07-17-health-profile-overclaim.md)
- [Problem: A2A dispatch compatibility](problems/2026-07-17-a2a-dispatch-compatibility.md)
- [Problem: agent MCP correlation](problems/2026-07-17-agent-mcp-correlation.md)

Definitions: [kagent capability matrix](../../docs/reference/kagent-capability-matrix.md).
Health profiles: [kagent health profiles](../../docs/reference/kagent-health-profiles.md).
Roadmap: [kagent educational roadmap](../../docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md).
