# kagent Agent-Mediated MCP Evidence Contract

Stable machine-readable contract for educational L6 proofs in the local kagent
lab. Producer: `scripts/kagent/agent_mcp_trace.py`. Consumer:
`scripts/kagent/KagentHealth.psm1` (`FullMcpExecution`).

Volatile live results belong in dated `evidence/kagent/` records.

## Schema version

`schemaVersion`: `"1.0"`
`evidenceKind`: `"agent-mediated-mcp"`

## Required semantics

A passing document must bind:

| Area | Requirement |
|------|-------------|
| Target | `clusterContext=docker-desktop`, `namespace=kagent`, `agent=k8s-a2a-agent`, `mcpServer=kagent-tool-server` |
| A2A | One `message/stream` dispatch only: HTTP 2xx transport; JSON-RPC 2.0 with matching request id and `error=null`; accepted dispatch; non-empty `taskOrMessageId`; state in `{submitted,working,completed,input_required}`; nested transport/protocol/dispatch fields agree with the outer A2A fields |
| Tool | `toolInvocation.observed=true`, tool `k8s_get_resources`, server `kagent-tool-server`, `correlatedTaskOrMessageId` equals A2A task id |
| Source | Protocol proof records the exact event/part index and sanitized structured marker. Log proof records one sanitized correlated line and its SHA-256 digest. The marker must bind the same task, `kagent-tool-server`, `k8s_get_resources`, and normalized `pod`/`kagent` arguments. |
| Result | Names are attributed only to same-task A2A agent/tool/model output at or after the tool observation; `returnedThroughA2A=true`; both name arrays are non-empty; recomputed subset match agrees with `matched=true` |
| Provenance | Canonical repo-relative `sourceEvidencePath`; referenced JSON content matches outer timestamp, target, task/request, tool proof, and result arrays; computed age <= 900 seconds; future skew <= 120 seconds; reported freshness agrees within 5 seconds; `targetBound=true`; `taskTraceCorrelated=true` |
| Decision | Complete `decision`; `passed=true` iff `exitCode=0`; `success` agrees; live collector `helperExit` agrees; exits retain `0` success, `1` capability gate, `2` malformed evidence, `3` collector/transport |

## Freshness

- `maxFreshnessSeconds`: **900**
- Reject `observedAt` more than **120** seconds in the future (clock skew)
- Recompute age from `observedAt`; do not trust a supplied freshness claim
- The producer queries `kubectl config current-context`; a caller-provided
  `--cluster-context` string cannot override the observed target

## Explicit rejects

- `evidenceKind=direct-mcp-tool-call` or any direct-MCP shortcut
- Model prose claiming a tool ran without a protocol or correlated log marker
- Missing/mismatched task IDs
- User-role markers, model prose, missing-task markers, wrong agent, controller,
  namespace, server, tool, or normalized arguments
- Missing, absolute, escaping, malformed, or content-mismatched
  `sourceEvidencePath`
- Cross-check mismatch, contradictory arrays, names emitted before the tool
  marker, or empty tool-derived/cross-check names
- Stale evidence; helper exit vs `decision` disagreement
- A separate A2A record whose task id differs from the Phase 5E task

## Bounded source capture

`sourceEvidencePath` is not a free-form note. The consumer opens the JSON under
the repository root and correlates it to the outer evidence. Protocol sources
must include non-negative `eventIndex` and `partIndex`. Log sources must include
the sanitized matched line and a digest whose reference is
`log:sha256:<first-16-hex>`.

If both bounded log collectors are unavailable, the producer exits 3. A
successful bounded search with zero correlated markers remains a truthful exit
1. A tool marker without same-task returned resource names cannot pass.

## Non-claims

- L4 dispatch alone is not L6
- RemoteMCPServer `Accepted=True` is not L6
- Direct MCP session smoke is not L6
- A profile pass does not replace dated evidence-index promotion review
