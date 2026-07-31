# Problem: Agent-mediated MCP correlation (L6)

**Date:** 2026-07-17
**Lane:** kagent educational lab
**Status:** Helper and nested evidence schema shipped; live L6 remains Not proven

## Symptom

Educational L6 requires A2A → agent → MCP tool → result → kubectl cross-check
with task/trace correlation. Prior gates could overclaim:

- Shallow flat `Test-AgentMediatedEvidenceObject` (no freshness, target binding,
  or ID correlation)
- Direct MCP success mistaken for agent mediation
- L4 `message/stream` acceptance without observable tool invocation

## Observed facts

- Agent allowlists RemoteMCPServer `kagent-tool-server` tools including
  `k8s_get_resources` (`deploy/samples/kagent/k8s-a2a-agent.yaml`)
- Phase 5D L4 Proven via `message/stream` SSE status-update + taskId
- Live Phase 5E helper: accepted `working` + non-empty taskId; **no** correlated
  tool marker in stream or bounded logs; exit 1; `toolInvocation.observed=false`
- kubectl can list pods in `kagent` independently (insufficient for L6)

## Root cause (correlation gap)

L6 needs an **observable** tool invocation bound to the same A2A task identifier.
Live runs reach accepted dispatch states but do not emit SSE function/tool parts
or log lines containing both `taskId` and `k8s_get_resources` before the run
fails closed. Without that observation, cross-check cannot validate tool-derived
names.

## Fix applied (no cluster upgrade)

1. `scripts/kagent/agent_mcp_trace.py` — fail-closed correlated collector
   (SSE markers or taskId+tool logs; kubectl cross-check; schema 1.0 JSON).
2. Nested `Test-AgentMediatedEvidenceObject` + FullMcpExecution collector
   invocation of the helper; reject `direct-mcp-tool-call`.
3. Deterministic pytest + Pester fixtures for pass and fail-closed cases.
4. Dated evidence recording truthful L6 Not proven while L4 remains Proven.

Evidence: `evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md`.

## Remaining promotion blocker

Obtain one live correlated tool observation (`k8s_get_resources` on
`kagent-tool-server` for the same taskId) with `result.matched=true` under the
versioned schema. Likely requires the agent model path to reach tool use
(credentials/quota) before terminal failure — not proven in this record.

## Review addendum — positive path hardened

The missing live tool observation remains the single P0 promotion blocker.
Deterministic review closed additional false-positive paths: stale or
future-dated claims, caller-spoofed context, user/prose markers, wrong
server/arguments, names before observation, contradictory result arrays,
missing decisions, helper/decision mismatches, escaping or malformed source
paths, source-content mismatches, and separate A2A/Phase 5E task ids.

`FullMcpExecution` now uses one Phase 5E dispatch and validates its embedded A2A
transport/protocol/dispatch. A valid source record is necessary but not enough:
the next closure evidence is still a fresh live helper exit 0 with one task id,
one correlated `kagent-tool-server` / `k8s_get_resources` marker, same-task
returned pod names, and a matching Kubernetes observation.
