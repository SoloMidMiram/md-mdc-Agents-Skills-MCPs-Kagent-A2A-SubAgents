# kagent Educational Roadmap

This document is a learning path for the local `kagent` lab. It separates what
you can observe today from what still requires A2A dispatch and real MCP-backed
tool execution.

It is intentionally educational. The project-wide engineering roadmap remains in
`docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`.

Canonical supporting documents:

- educational-lane boundary: `docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md`
- problem workflow: `docs/runbooks/educational-problem-manual.md`
- capability definitions: `docs/reference/kagent-capability-matrix.md`
- current evidence/status: `evidence/kagent/README.md`
- documentation placement rules: `docs/DOCUMENTATION-ORGANIZATION.md`

## Where You Are Now

The basic observation lab is usable now:

- the local `kagent` namespace exists on the Docker Desktop Kubernetes cluster
- kagent pods, services, agents, events, and RemoteMCPServer resources can be inspected
- the kagent UI can be opened through a port-forward
- the sample `k8s-a2a-agent` can be inspected through the controller REST API
- `RemoteMCPServer/kagent-tool-server` is `Accepted=True` with the phase 4 runtime deployed; `kagent-grafana-mcp` remains an out-of-scope degraded dependency

Two learning levels after phase 5e:

- real A2A task dispatch is **proven** (phase 5d `message/stream`)
- real MCP-backed execution through the agent is **not** proven (L6); phase 5e
  shipped correlated gates and recorded a truthful live failure (no tool marker);
  direct MCP access and L5 acceptance are proven

Use this distinction throughout the lab: an accepted agent is not the same thing
as a tool-invoking agent.

## First Practice: Observe and Measure

This first practice teaches the kagent control plane without requiring real MCP
tool execution.

### 1. Run the health checker

```powershell
.\scripts\kagent\check-kagent-health.ps1
```

Expected learning:

- pod readiness shows whether the kagent control plane is healthy
- agent status shows whether agents are accepted and ready
- RemoteMCPServer status shows whether backing MCP endpoints are reachable
- service hints show which port-forwards to run next

What this proves:

- kagent is reconciled enough for observation and card/acceptance testing

What this does not prove:

- A2A task dispatch
- real MCP tool invocation

### 2. Inspect pods, agents, and RemoteMCPServer resources

```powershell
kubectl get pods -n kagent
kubectl get agent -n kagent
kubectl get remotemcpserver -n kagent
kubectl describe remotemcpserver kagent-tool-server -n kagent
```

Expected learning:

- pods are the running control-plane and workload processes
- agents are kagent custom resources reconciled by the controller
- RemoteMCPServer resources are references to MCP endpoints
- `Accepted=True` on `kagent-tool-server` means the controller can reach and discover its real MCP server; it still does not prove agent-mediated invocation

What this proves:

- the resources exist and their current status is observable

What this does not prove:

- the target MCP service exists
- the declared tools can actually be invoked

### 3. Open the kagent UI

Run this in a terminal that can stay open:

```powershell
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```

Then open:

```text
http://localhost:8080
```

Expected learning:

- the UI is a view over the local kagent control plane
- UI reachability is useful evidence, but it is not task-execution evidence

What this proves:

- the UI service is reachable through the port-forward

What this does not prove:

- A2A dispatch
- MCP tool execution

### 4. Fetch the sample agent details

Run this in a second terminal:

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
```

Then fetch the card/details:

```powershell
python scripts/kagent/test-a2a-agent.py card
curl.exe http://localhost:8083/api/agents/kagent/k8s-a2a-agent
```

Expected learning:

- the sample agent is visible through the controller REST API
- the card/details show accepted state, deployment readiness, model, and skills
- this is the current reliable educational endpoint

What this proves:

- the controller can return agent metadata
- the sample agent is configured and discoverable

What this does not prove:

- JSON-RPC task dispatch works
- the tools named in the agent can be called

### 5. Observe `RemoteMCPServer Accepted=False`

Historical state before applying the phase 4 runtime:

```text
kagent-tool-server ... Accepted=False
```

Why this was expected in phases 0-2:

- `deploy/base/kagent/kagent-tool-server.yaml` points to `http://kagent-tool-server.kagent:8000/mcp`
- no real MCP server was deployed at that address during phases 0-2
- those phases only needed the resource to exist for card and acceptance inspection

After phase 4, `kagent-tool-server` is expected to be `Accepted=True`. An
`Accepted=False` result now means the runtime or its Service needs diagnosis.

When this becomes unacceptable:

- any phase that claims real MCP tool execution
- any phase that claims the agent can use `k8s_get_resources`
- any health profile named `FullMcpExecution`

## phase_N Roadmap

| Phase | Purpose | Commands | What to observe | Success evidence | What it does not prove yet |
|-------|---------|----------|-----------------|------------------|----------------------------|
| `phase_0_observe` | Learn the kagent control plane and current resource health. | `.\scripts\kagent\check-kagent-health.ps1`; `kubectl get pods -n kagent`; `kubectl get agent -n kagent`; `kubectl get events -n kagent --sort-by=.lastTimestamp` | pods, agents, events, service hints, summary counts | health checker exits 0 for the card lab; pods and agents are visible | A2A task dispatch or MCP tool execution |
| `phase_1_ui_and_card` | Learn UI and controller REST inspection. | `kubectl port-forward -n kagent svc/kagent-ui 8080:8080`; `kubectl port-forward -n kagent svc/kagent-controller 8083:8083`; `python scripts/kagent/test-a2a-agent.py card`; `curl.exe http://localhost:8083/api/agents/kagent/k8s-a2a-agent` | UI reachability, accepted agent details, skills, model metadata | UI opens; card/details return `Accepted: True` and `DeploymentReady: True` | task dispatch or tool invocation |
| `phase_2_degraded_mcp_understanding` | Understand why `RemoteMCPServer Accepted=False` was expected before the phase 4 runtime. | `kubectl get remotemcpserver -n kagent`; `kubectl describe remotemcpserver kagent-tool-server -n kagent`; inspect `deploy/base/kagent/kagent-tool-server.yaml` | historical target URL, accepted condition, and missing service | learner can explain why `Accepted=False` was acceptable for card labs only | full MCP execution |
| `phase_3_truthful_a2a_dispatch` | Separate `card`, `probe`, `task`, and `both` into truthful learning gates. | `python scripts/kagent/test-a2a-agent.py card`; `python scripts/kagent/test-a2a-agent.py probe`; `python scripts/kagent/test-a2a-agent.py task`; `python scripts/kagent/test-a2a-agent.py both` | which paths inspect metadata, which paths test protocol support, which paths must fail on unavailable dispatch | `task` fails when dispatch is unavailable; `probe` reports neutrally; `both` passes only when card and task pass | MCP tool execution |
| `phase_4_real_mcp_server` | Deploy a lightweight in-cluster MCP server behind `kagent-tool-server`. | `kubectl apply -f deploy/base/kagent/kagent-tool-server-runtime.yaml` (reusable base); `kubectl get remotemcpserver -n kagent` checks acceptance | service, endpoint, tool discovery, RemoteMCPServer acceptance | `RemoteMCPServer/kagent-tool-server` reached `Accepted=True` on 2026-07-16 (94 tools discovered) | that the agent has invoked a tool |
| `phase_5_real_agentic_work` | Attempt to prove A2A task dispatch (L4) and agent -> MCP tool invocation (L6). | Existing helper (`card`/`task`/`probe`/`both`); A2A `message/send` with spec-compliant payloads; direct MCP initialize smoke test; UI inspection | task request, agent response, tool result | `message/send` is registered but fails internally; direct MCP initialize succeeds but `tools/call` fails; L4 and L6 remain unproven | repeatable workshop setup |
| `phase_5b_direct_mcp_session` | Close the direct-client MCP session-reuse problem without implying agent mediation. | `python scripts/kagent/mcp_session_smoke.py --url http://127.0.0.1:8000/mcp --output json --resource-type pod --resource-namespace kagent` | initialize, initialized notification, discovered schema, session-reusing tool call, cleanup | exit 0; 18 pods matched `kubectl`; direct MCP invocation proven | L4 A2A dispatch or L6 agent-mediated invocation |
| `phase_5c_truthful_health_profiles` | Teach that “healthy” depends on the capability under test via named profiles. | Run `.\scripts\kagent\check-kagent-health.ps1 -Profile <Profile>` separately for `CardLab`, `DirectMcpServer`, `A2ADispatch`, and `FullMcpExecution` | distinct pass/fail decisions from the same cluster | CardLab/DirectMcpServer pass; A2ADispatch/FullMcpExecution fail truthfully ([phase 5c](../../evidence/kagent/educational-practice-phase-5c-health-profiles.md)) | L4 or L6 becoming proven |
| `phase_5d_trustworthy_a2a` | Prove L4 with pinned `message/stream` and strict JSON evidence. | `python scripts/kagent/test-a2a-agent.py task --output json`; `.\scripts\kagent\check-kagent-health.ps1 -Profile A2ADispatch` | SSE status-update with non-empty taskId; health JSON gate | L4 proven ([phase 5d](../../evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md)); A2ADispatch exit 0 | L6 agent-mediated MCP |
| `phase_5e_agent_mediated_mcp` | Correlate one A2A task → MCP `k8s_get_resources` → same-task returned names → kubectl match under nested schema 1.0. | `python scripts/kagent/agent_mcp_trace.py --output json`; FullMcpExecution profile | agreeing transport/protocol/dispatch; exact task/server/tool/arguments; bounded source proof; computed freshness; recomputed name match | Hardened helper/schema/tests shipped; retained live exit 1 — L6 Not proven ([phase 5e](../../evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md)) | Live L6 without one fresh exit 0 |
| `phase_5f_integrity_and_protocol_hardening` | Close reproducible fail-closed defects before relying on stricter health or A2A evidence gates. | Targeted Pester and pytest cases for missing CRDs and multiline SSE; repository hygiene checks | strict health profiles reject a missing `RemoteMCPServer` CRD; multi-line SSE `data:` fields form one JSON payload; local debug captures are not tracked | fixes and deterministic regression tests are merged; hosted CI status is recorded only for the exact committed head | L6, IDE discovery, or a green run at an unverified SHA |
| `phase_6_native_mcp_federation` | Verify the controller's native MCP contract before exposing any IDE-facing bridge. | `controller_mcp_smoke.py --output json`; project Cursor/Codex configuration; `initialize`, `tools/list`, `list_agents`, bounded `invoke_agent` | negotiated controller protocol, reviewed tool schemas, target discovery, bounded response, and same-session continuation | I0-I2 are recorded in [phase 6](../../evidence/kagent/educational-practice-phase-6-native-mcp-federation.md); I3 requires a valid bounded agent response | L6 tool invocation, autonomous mutation, or an alternate gateway |
| `phase_7_readonly_l6_end_to_end` | Make the runtime natively read-only, then correlate one normal IDE invocation through agent tooling to Kubernetes. | native read-only schema discovery; one controller `invoke_agent`; `agent_mcp_trace.py --output json`; `FullMcpExecution` profile | mutation tools absent; same invocation/task identity; `k8s_get_resources`; returned pod names; `kubectl` match | one qualifying I4 and L6 record; three consecutive successes recommended for operational confidence | L7 repeatability or reverse delegation |
| `phase_8_repeatable_native_runtime` | Make the proven native read-only IDE path reproducible for a fresh learner. | start, check, stop, restart, project configuration, acceptance, and cleanup commands | pinned prerequisites; both-client acceptance; no orphaned port-forwards or lab resources | clean Docker Desktop run reaches I5 and L7 targets with dated evidence | production readiness or a write-enabled profile |

## Strategic Upper-Layer Grid

The canonical L0-L7 definitions and promotion rules are maintained in
`docs/reference/kagent-capability-matrix.md`. The current decision for each level
is maintained in `evidence/kagent/README.md`; this roadmap owns phase sequencing.

## Rules Before Real MCP/Agentic Work

### Boundaries

- Do not call `Accepted=True` agent status "tool execution."
- Do not let `probe` success imply `task` success.
- Do not promote `RemoteMCPServer Accepted=False` beyond card and acceptance labs.
- Keep card/metadata inspection separate from task dispatch.
- Keep task dispatch separate from MCP tool invocation.
- Treat direct A2A helpers as protocol-conformance and evidence diagnostics.
  Cursor and Codex use the controller's native `/mcp` surface when the pinned
  contract exposes the required agent tools.

### Promotion Rules

- A phase can only depend on evidence from the previous phase if that evidence is observable and recorded.
- Do not move from L3 to L4 until `task` mode has truthful pass/fail semantics.
- Do not move from L4 to L5 until a real MCP server manifest and service are separate from the sample agent.
- Do not move from L5 to L6 until a task response proves a real tool was invoked.

### Validation Gates

- Add health-check profiles before making stricter requirements global.
- `CardLab` may allow unrelated RemoteMCPServer `Accepted=False`.
- `DirectMcpServer` requires target acceptance plus session-reusing direct tool evidence.
- `A2ADispatch` must require truthful task dispatch behavior.
- `FullMcpExecution` must derive A2A and agent-mediated tool gates from the same
  Phase 5E task; any separately supplied A2A record must have the same task id.
  Direct MCP alone is insufficient.

### Naming Rules

- Use `card` only for metadata/card retrieval.
- Use `probe` only for method support discovery.
- Use `task` only for actual dispatch attempts.
- Use `both` only when both card validation and task dispatch are required.
- Do not name a function `fetch_agent_card` if it sends a task payload.

### Deploy Taxonomy

- `deploy/base/` contains reusable primitives such as `RemoteMCPServer` definitions.
- `deploy/samples/` contains educational starter agents and examples.
- Real MCP server manifests must be separate from sample A2A agent manifests.
- Environment-specific assembly belongs in future overlays, not in the sample manifest.

### Evidence Requirements

- Capture evidence for completed phases under `evidence/` or in the relevant runbook.
- Evidence must include the command, observed output summary, date, and capability level proven.
- Do not reuse L2 or L3 evidence to claim L5 or L6.
- Record unexpected implementation failures with
  `docs/templates/educational-problem-record.md`; promote only proven recurring
  diagnostics into this roadmap or the runbook.

Completed phases are recorded in `evidence/kagent/educational-practice-phase-0-2.md`.
The implementation review is recorded in
`evidence/kagent/educational-practice-phase-0-2-review.md`.
Truthful A2A dispatch gate evidence is recorded in
`evidence/kagent/educational-practice-phase-3.md`.
Real MCP server design and L5 acceptance evidence is recorded in
`evidence/kagent/educational-practice-phase-4.md`.
The MCP server design decision record is at
`evidence/kagent/educational-practice-phase-4a-design.md`.
A2A dispatch check and agentic work attempt for L4/L6 is recorded in
`evidence/kagent/educational-practice-phase-5.md` (L4 and L6 remain unproven).
The direct-client session follow-up is recorded in
`evidence/kagent/educational-practice-phase-5b-direct-mcp.md`; it proves direct
MCP invocation only.
Truthful health profiles are recorded in
`evidence/kagent/educational-practice-phase-5c-health-profiles.md`.
Trustworthy A2A dispatch (L4) is recorded in
`evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md`.
Correlated agent-mediated MCP attempt (L6 Not proven) is recorded in
`evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md`.

## Next Implementation Slices

1. (DONE) Fix `scripts/kagent/test-a2a-agent.py` task semantics so unavailable dispatch exits non-zero.
2. (DONE) Named health profiles on `check-kagent-health.ps1` /
   `KagentHealth.psm1`: `CardLab`, `DirectMcpServer`, `A2ADispatch`,
   `FullMcpExecution`. Evidence:
   `evidence/kagent/educational-practice-phase-5c-health-profiles.md`.
3. (DONE) Add a minimal real MCP server behind `kagent-tool-server`.
4. (DONE) Direct MCP session smoke helper
   (`scripts/kagent/mcp_session_smoke.py`) with mandatory lifecycle, `tools/list`
   schema discovery, and session reuse. Live evidence:
   `evidence/kagent/educational-practice-phase-5b-direct-mcp.md`. Direct MCP is
   server evidence only; it does not prove L6.
5. (DONE) Resolve A2A dispatch for L4 via pinned `message/stream` SSE path and
   strict JSON evidence. Evidence:
   `evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md`.
6. (DONE) Replace human-output scraping with versioned JSON from the A2A helper
   and require a recognized response/task shape before L4 promotion.
7. (DONE) Nested agent-mediated schema with single-task A2A agreement,
   recomputed freshness, observed target binding, bounded source-content
   validation, exact tool arguments, recomputed result arrays, and exit
   consistency (`agent_mcp_trace.py`, FullMcpExecution). Evidence: phase 5e
   (live L6 Not proven; hardened positive path deterministic-only).
8. (DONE) Fix strict health-profile handling of a missing `RemoteMCPServer` CRD: allow
   it only for `CardLab`; make `DirectMcpServer`, `A2ADispatch`, and
   `FullMcpExecution` exit 3 with deterministic Pester coverage.
9. (DONE) Make `parse_sse_jsonrpc_events()` compliant with multi-line SSE `data:`
   fields: normalize CRLF, join each event's data lines, ignore comments and
   `[DONE]`, and test malformed combined payloads.
10. (DONE) Reconcile repository hygiene and hosted CI truth for the current
    committed head: retain only local debug captures under ignore rules, and
    update current status prose only after the exact workflow run is observed.
    Quality run `30621919672` passed at `94031ff` on 2026-07-31. That revision
    is now part of merged PR #1 and remains historical CI context rather than
    an active merge gate; capability decisions are unchanged.

**Delivery sequence:** PR #3 delivers the Phase 6 native-federation foundation
(I0-I2 Proven; I3 remains Blocked). A Phase 7 PR follows for read-only I4/L6
proof, then a Phase 8 PR for repeatable I5/L7. These are dependency-ordered,
not date-estimated. Items 11-13 below map one-to-one to these PRs.

11. Native controller MCP federation: record the live `initialize`, `tools/list`,
    and `list_agents` contract; maintain project-scoped Cursor/Codex configs
    against that one endpoint. I0-I2 are proven for controller 0.9.11. I3 is
    blocked until the provider region policy permits a bounded no-tool response.
    Do not build a custom Cursor/Codex-to-A2A bridge.
12. Make the MCP runtime natively read-only and obtain one same-invocation
    IDE -> agent -> MCP tool -> kubectl-matched loop to promote I4 and L6.
    Retain restrictive RBAC. Treat model credentials, provider availability,
    resolved skills, schema validity, and timeout as hypotheses until observed.
13. Build the repeatable native workshop/bootstrap and cleanup path only after
    the full read-only IDE correlation succeeds; it must validate both clients
    before awarding I5 or L7.

## Major Flaws To Close

The ranked flaw ledger is maintained in `evidence/kagent/README.md`. Roadmap
ownership is:

1. **P0 L6:** obtain one live correlated tool observation with kubectl match
   (helper/schema already fail closed).
2. **P1 runtime safety:** move to a native read-only MCP image while retaining
   restrictive RBAC.
3. **P1 native federation:** restore provider access for the recorded
   `invoke_agent` region-policy block; do not mistake its HTTP response for a
   completed agent task.
4. **P2 documentation drift:** continue replacing repeated runtime snapshots
   with links to `evidence/kagent/README.md`.
