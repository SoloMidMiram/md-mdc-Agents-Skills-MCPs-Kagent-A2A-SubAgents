# kagent Educational Practice: Phase 5B Direct MCP Evidence

## Meta

| Field | Value |
|-------|-------|
| Date | 2026-07-17 |
| Timezone | UTC+3:30 |
| Machine | Windows (win32 10.0.26200) |
| Cluster | Docker Desktop (context: `docker-desktop`) |
| Namespace | `kagent` |
| Practice | phase_5 follow-up — direct MCP session reuse |
| Image | `ghcr.io/kagent-dev/kagent/tools:0.0.13` |

## Prerequisite

```powershell
kubectl port-forward -n kagent svc/kagent-tool-server 8000:8000
```

## Exact Command

```powershell
uv run --python 3.12 python scripts/kagent/mcp_session_smoke.py `
  --url http://127.0.0.1:8000/mcp `
  --output json `
  --resource-type pod `
  --resource-namespace kagent
```

Exit code: **0**

## Observed Results (sanitized)

| Stage | Result |
|-------|--------|
| requestedProtocolVersion | `2024-11-05` |
| negotiatedProtocolVersion | `2024-11-05` |
| transportObservation | `observed-streamable-http-compatibility` |
| sessionId | `present` (value never printed) |
| initializedHttpStatus | `202` |
| initializedCompatibilityDeviation | `false` |
| tools/list schema properties | `all_namespaces`, `namespace`, `output`, `resource_name`, `resource_type` |
| tool | `k8s_get_resources` |
| toolCallSucceeded | `true` |
| resourceSummary.count | `18` |
| resourceSummary.sampleNames | first five pod names in `kagent` (sanitized list) |
| cleanup | `deleted` |

## kubectl Cross-Check

```powershell
kubectl get pods -n kagent --no-headers
```

Observed pod count: **18** — matches `resourceSummary.count`.

## Capability Proved

- Direct MCP tool invocation with session reuse against the in-cluster
  `kagent-tool-server` endpoint (server evidence only).

## Explicit Non-Claims

- **Not L4:** no A2A task/message dispatch was exercised.
- **Not L6:** no agent-mediated tool invocation; this was a direct MCP client call.
- Does not change RemoteMCPServer acceptance (already L5) into tool-invocation proof through the agent path.

## Related Records

- Original failure: [phase 5](educational-practice-phase-5.md) Subphase 5B
- Problem record: [2026-07-17 MCP session reuse](problems/2026-07-17-mcp-session-reuse.md)
- Helper: `scripts/kagent/mcp_session_smoke.py`
