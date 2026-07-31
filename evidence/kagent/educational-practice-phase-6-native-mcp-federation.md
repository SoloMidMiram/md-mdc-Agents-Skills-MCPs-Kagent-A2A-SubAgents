# Phase 6 Native MCP Federation Observation

**Observed:** 2026-07-31, Asia/Tehran
**Environment:** Docker Desktop Kubernetes context `docker-desktop`, namespace `kagent`
**Controller:** Helm chart `kagent-0.9.11`; image
`ghcr.io/kagent-dev/kagent/controller:0.9.11`

## Commands

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
python scripts/kagent/controller_mcp_smoke.py --output json
```

The helper performed one Streamable HTTP MCP lifecycle: `initialize`,
`notifications/initialized`, `tools/list`, `list_agents`, one bounded
`invoke_agent`, and a same-MCP-session `list_agents` reuse check on its
successful path. It never writes a raw MCP session identifier to output.
See the 2026-07-31 addendum for later field-name and I3-requirement
clarifications.

## Observed contract

`http://127.0.0.1:8083/mcp` returned a 200 SSE `initialize` response with
protocol `2024-11-05`, server name `kagent-agents`, version `0.9.11`, and a
session identifier. `notifications/initialized` returned 202. `tools/list`
returned exactly `list_agents` and `invoke_agent` with the expected pinned
schemas. `list_agents` returned `kagent/k8s-a2a-agent` in structured content.

The bounded `invoke_agent` request returned HTTP 200 but its structured agent
text reported an OpenAI provider `403` for an unsupported country, region, or
territory. The helper exited 1 because it did not receive the required no-tool
response. This is an external provider blocker, not an MCP or Kubernetes tool
success. A separate manual same-session `list_agents` continuation completed
with HTTP 200 before this helper was added.

## Native IDE-federation decision

| Level | Decision | Evidence |
|-------|----------|----------|
| I0 | Proven | Controller `/mcp` initialized through the local port-forward. |
| I1 | Proven | `tools/list` returned the two expected controller tools and no unreviewed tool. |
| I2 | Proven | `list_agents` returned `kagent/k8s-a2a-agent` in structured content. |
| I3 | Blocked | Provider region policy prevented a successful bounded agent response. |
| I4 | Not proven | No IDE invocation has correlated with a tool-derived Kubernetes result. |
| I5 | Not attempted | No fresh setup, restart, and cleanup acceptance record exists. |

## Explicit non-claims

- A controller MCP handshake, agent discovery, and an HTTP 200 tool result do
  not prove that the agent completed the requested task.
- This observation does not prove L6: no `k8s_get_resources` invocation,
  returned pod names, same-task tool identity, or independent `kubectl` match
  was observed.
- The controller's native contract is present, so a custom A2A-to-MCP gateway
  remains deferred and unjustified.

## Addendum — 2026-07-31 correction cycle (interpretation)

Field naming and I3 requirements were tightened without promoting capability:

- JSON/Python fields formerly named as "same-session continuation" now mean
  MCP-session reuse only (`sameMcpSessionReuseHttpStatus`,
  `mcpSessionReuseTargetPresent`). Agent-context continuation is a separate
  `invoke_agent` follow-up using `context_id` and is recorded as
  `agentContextId` / `agentContextContinuationSucceeded` without raw ids.
- HTTP 405 cleanup remains `method-not-allowed`: explicit MCP session
  termination was attempted but is unsupported by the pinned controller; this
  is not proof the session was deleted. Phase 8 cleanup remains separate.
- Generic Python `controller_mcp_smoke.py` success is a prerequisite diagnostic,
  not I3. I3 requires a real IDE client; Cursor is the lead-client gate.
- Provider blocker re-checked without reading secret values: ModelConfig
  `default-model-config` remains OpenAI/`gpt-4.1-mini` with `Accepted=True`;
  Secret `kagent-openai` exists with key `OPENAI_API_KEY` (non-empty). The
  observed `403` unsupported-country/region/territory response is unchanged.
  Supported replacement path: supply a region-allowed OpenAI credential for the
  existing secret key, or point `default-model-config` at another provider the
  pinned kagent `0.9.11` chart supports, then re-run bounded acceptance. No
  credentials were rotated in this correction cycle.
- I3 remains Blocked / Not proven until a dated Cursor UI acceptance record
  qualifies. I3 still does not imply L6.
