# Educational practice — Phase 5E: Correlated agent-mediated MCP

**Date:** 2026-07-17
**Timezone:** UTC (observedAt timestamps)
**Environment:** local Docker Desktop Kubernetes; namespace `kagent`
**Controller image:** `ghcr.io/kagent-dev/kagent/controller:0.9.11`
**Agent:** `k8s-a2a-agent` (`golang-adk`)
**MCP server:** RemoteMCPServer `kagent-tool-server` (tools allowlisted include
`k8s_get_resources`)
**Helm:** no upgrade performed

## Objective

Prove L6 only with correlated evidence: A2A `message/stream` → agent → MCP tool
`k8s_get_resources` on `kagent-tool-server` → tool-derived names → kubectl
cross-check, under a versioned nested evidence schema. Keep L4 Proven.

## Facts (observed)

| Observation | Classification |
|-------------|----------------|
| Agent YAML allowlists `k8s_get_resources` / `k8s_get_available_api_resources` via RemoteMCPServer `kagent-tool-server` | Wiring present (not L6) |
| L4 remains Proven via Phase 5D `message/stream` status-update + taskId | Unchanged |
| Live helper run: `taskOrMessageId=019f70aa-0a6b-7052-8f8a-104afbf6a355`, `acceptedState=working` | L4 semantics preserved |
| Live stream/events + bounded agent/controller logs: no correlated `k8s_get_resources` tool marker for that taskId | No tool observation |
| `toolInvocation.observed=false`; `result.matched=false`; helper exit **1** | Fail-closed L6 |
| kubectl cross-check listed 18 pods in `kagent` (baseline only; unused without tool names) | Cluster readable |

## Inference (labeled)

Model quota / early terminal `failed` after accepted `working` likely prevented
tool use before MCP invocation. This is an inference from prior Phase 5D
streams and agent Execute logs without tool tokens; it is not proven as the sole
cause. Absence of observable tool markers alone is sufficient to keep L6 Not
proven.

## Deterministic work

- Added `scripts/kagent/agent_mcp_trace.py` (stdlib): reuses Phase 5D transport
  via importlib of `test-a2a-agent.py`; emits schema 1.0 nested JSON; exits
  0/1/2/3.
- Additive `collect_dispatch_stream()` in `test-a2a-agent.py` (L4 gate unchanged).
- Schema reference: `docs/reference/kagent-agent-mediated-mcp-evidence.md`.
- `Test-AgentMediatedEvidenceObject` requires nested freshness, target binding,
  tool observation, ID correlation, `result.matched`, and decision/exit agreement;
  rejects `direct-mcp-tool-call`.
- `FullMcpExecution` collector may invoke `agent_mcp_trace.py --output json` when
  `-AgentToolEvidencePath` is omitted; never scrapes human text. `A2ADispatch`
  path unchanged.
- Tests: `tests/kagent/test_agent_mcp_trace.py` (10 passed); Pester 3.4
  `KagentHealth.Tests.ps1` FullMcpExecution nested fixtures (52 passed).

## Live commands and exits

Controller listener on `127.0.0.1:8083` reused (existing PID; not stopped).

```text
uv run python scripts/kagent/agent_mcp_trace.py `
  --controller http://127.0.0.1:8083 `
  --output json `
  --source-out evidence/kagent/tmp/agent-mcp-trace-latest.json
→ exit 1
  a2a.taskOrMessageId=019f70aa-0a6b-7052-8f8a-104afbf6a355
  a2a.acceptedState=working
  toolInvocation.observed=false
  result.matched=false
  decision.reason=no observable MCP tool invocation correlated to A2A task
    (L4 accepted=True state=working)
```

Sanitized source capture path (gitignored tmp):
`evidence/kagent/tmp/agent-mcp-trace-latest.json`.

## Decision

| Level | Decision | Basis |
|-------|----------|-------|
| L4 | **Proven** (unchanged) | Phase 5D + live accepted `working` + non-empty taskId on this run |
| L6 | **Not proven** | No SSE/log tool marker for `k8s_get_resources` correlated to the task; no tool-derived names; `matched=false`; exit 1 |

## Non-claims

- Direct MCP (`mcp_session_smoke.py`) is not L6.
- RemoteMCPServer `Accepted=True` / tools/list is not L6.
- L4 dispatch alone is not L6.
- Model prose naming pods without an explicit tool/function part or correlated
  log line is not L6.
- Helper/schema/tests existence is not L6 Proven.
- No automatic capability-matrix promotion without dated correlated evidence.

## Blockers for L6 Proven

1. Obtain one live stream (or correlated agent/controller log) that names
   `k8s_get_resources` / `kagent-tool-server` with the same `taskId`.
2. Extract tool-derived pod names and satisfy kubectl cross-check
   (`matched=true`, non-empty intersection, no extra claimed names).
3. Keep freshness ≤ 900s and nested schema 1.0 fields intact for
   `FullMcpExecution`.

Likely operational prerequisites (not proven here): working model credentials /
quota so the agent reaches tool use before terminal failure.

## Related

- Schema: `docs/reference/kagent-agent-mediated-mcp-evidence.md`
- Problem: `evidence/kagent/problems/2026-07-17-agent-mcp-correlation.md`
- Prior L4: `evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md`

## Review addendum — positive-gate hardening

The live observation above is preserved unchanged. A later same-day review
found that the deterministic positive gate was more permissive than this record
claimed. Schema/CLI version `1.0` and exit codes remain unchanged, but a passing
record now requires:

- one Phase 5E dispatch; `FullMcpExecution` derives L4 from its embedded A2A
  transport/protocol/dispatch fields instead of sending a second task;
- exact observed target (`docker-desktop`, `kagent`, `k8s-a2a-agent`, controller
  origin), server, tool, and normalized `pod`/`kagent` arguments;
- an agent/tool/model structured marker bound to the exact task; user markers,
  prose, wrong/missing task/server/arguments, and names before the marker are
  ignored;
- bounded protocol event/part proof or a sanitized correlated log line plus
  digest; both unavailable log collectors classify as exit 3, while a completed
  search with no marker remains exit 1;
- same-task returned names, independently collected Kubernetes names, and a
  recomputed match rather than trusting `matched=true`;
- computed freshness (`maxFreshnessSeconds=900`, future skew <=120s), complete
  decision/helper-exit agreement, and parsing/correlation of the repo-contained
  `sourceEvidencePath` JSON.

Deterministic review result: `tests/kagent/test_agent_mcp_trace.py` **17/17**;
the combined Phase 5B/5D/5E Python suites **99/99**; Pester 3.4.0 health suite
**64/64**. Pester 5.7.1 is installed, but the suite
intentionally uses legacy Pester 3 `Should Be` syntax and reports **0/64**
there; that compatibility result is separate from product behavior.

No controller listener was present on port 8083 during the hardening review, so
no additional task was sent. The hardened positive path is deterministic-only;
the recorded live exit 1 remains the current L6 decision.

Exact observation commands used for the retained environment facts:

```powershell
kubectl config current-context
kubectl get pods -n kagent --no-headers
kubectl get agent -n kagent --no-headers
kubectl get remotemcpserver -n kagent --no-headers
kubectl get deployment kagent-controller -n kagent `
  -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl get deployment k8s-a2a-agent -n kagent `
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```
