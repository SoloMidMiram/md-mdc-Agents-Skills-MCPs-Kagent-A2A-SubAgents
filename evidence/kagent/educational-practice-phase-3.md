# kagent Educational Practice: Phase 3 Evidence

## Meta

| Field | Value |
|-------|-------|
| Date | 2026-07-16 |
| Time | 15:10 - 15:12 UTC+3:30 |
| Machine | Windows |
| Cluster | Docker Desktop, namespace `kagent` |
| Practice | `phase_3_truthful_a2a_dispatch` |

## Goal

Make the A2A helper report each learning gate truthfully:

- `card` proves REST/card metadata visibility only.
- `probe` reports JSON-RPC method support neutrally.
- `task` proves dispatch only when a task is accepted or completed.
- `both` passes only when both card validation and task dispatch pass.

This phase does not implement a real MCP server and does not prove real MCP tool
execution.

## Implementation Summary

`scripts/kagent/test-a2a-agent.py` was updated so that task dispatch errors are
real failures. In particular, JSON-RPC `-32601` now exits non-zero for `task`
and `both`.

The misleading JSON-RPC card helper was removed. Card validation now uses the
controller REST API path and requires accepted/deployment-ready fields to be
present in the returned metadata.

`probe` remains informational: unsupported methods are reported without claiming
task success.

## Commands Run

All commands ran from `F:\Git\MCPtest`.

### Controller Reachability

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8083/health
```

Result:

- Exit code: 0
- Output: `200`
- Interpretation: controller port-forward was already active and reachable.

### `card`

```powershell
python scripts\kagent\test-a2a-agent.py card
```

Result:

- Exit code: 0
- Agent: `kagent/k8s-a2a-agent`
- Accepted: `True`
- DeploymentReady: `True`
- Model: `gpt-4.1-mini (OpenAI)`
- Skill: `get-resources-skill`

Capability proven:

- L3 Agent details/card observable

Capability not proven:

- L4 A2A task dispatch

### `probe`

```powershell
python scripts\kagent\test-a2a-agent.py probe
```

Result:

- Exit code: 0
- `tasks/sendTask`: `error code=-32601: method not found`
- `message/send`: `error code=-32603: failed to decode response`
- `agent/getAgentCard`: `error code=-32601: method not found`

Interpretation:

- JSON-RPC method support was probed.
- Unsupported methods were reported neutrally.
- This does not prove task dispatch.

### `task`

```powershell
python scripts\kagent\test-a2a-agent.py task
```

Result:

- Exit code: 1
- Dispatch failed with JSON-RPC code `-32601`
- Message summary: `method not found`
- Script output explicitly states: `L4 A2A task dispatch is NOT proven`

Interpretation:

- The helper now fails truthfully when dispatch is unavailable.
- L4 remains not proven.

### `both`

```powershell
python scripts\kagent\test-a2a-agent.py both
```

Result:

- Exit code: 1
- Card validation succeeded.
- Task dispatch failed with JSON-RPC code `-32601`.

Interpretation:

- `both` now depends on both card success and real task dispatch success.
- This is the expected truthful result for the current controller behavior.

### Optional Cluster Checks

The first sandboxed direct `kubectl` checks could not read
`C:\Users\cebit.ir\.kube\config`. The checks were rerun with kubeconfig access
allowed.

```powershell
.\scripts\kagent\check-kagent-health.ps1
kubectl get agent -n kagent
kubectl get remotemcpserver -n kagent
```

Results:

- `check-kagent-health.ps1`: exit code 0
- 17/17 pods ready
- 11/11 agents accepted+ready
- 2 RemoteMCPServer resources present
- 0 RemoteMCPServer resources accepted
- `kagent-tool-server`: `Accepted=False`
- `kagent-grafana-mcp`: `Accepted=False`

## Capability Level Assessment

| Level | Description | Decision | Evidence |
|-------|-------------|----------|----------|
| L0 | Config exists | Proven | manifests, roadmap, helper, evidence files exist |
| L1 | Control plane healthy | Proven | health checker exits 0; 17/17 pods ready |
| L2 | Agent accepted/ready | Proven | 11/11 agents Accepted=True and Ready=True |
| L3 | Agent details/card observable | Proven | `card` exits 0 and returns metadata |
| L4 | A2A task dispatch works | Not proven | `task` exits 1 with `-32601 method not found` |
| L5 | RemoteMCPServer accepted | Not proven | both RemoteMCPServers are Accepted=False |
| L6 | Tool invocation proven | Not proven | no MCP tool invocation result recorded |
| L7 | Repeatable workshop/install path | Not proven | no bootstrap/cleanup automation exercised |

## Guardrails Compliance

- `Accepted=True` is treated as reconciliation evidence, not tool execution.
- `card` success is not treated as task success.
- `probe` success is not treated as task success.
- `task` failure prevents L4 from being claimed.
- `both` failure confirms the combined gate is now truthful.
- `RemoteMCPServer Accepted=False` remains acceptable only for card/acceptance labs.

## Unaddressed Problems

- L4 task dispatch remains unresolved while `tasks/sendTask` returns `-32601`.
- L5 RemoteMCPServer acceptance remains unresolved until `kagent-tool-server` reaches `Accepted=True`.
- L6 tool invocation remains unresolved until task -> agent -> MCP tool -> result is recorded.
- L7 repeatable workshop remains unresolved until bootstrap and cleanup automation exists.

## Next Recommended Step

Proceed to `phase_4_real_mcp_server` only after deciding which lightweight MCP
server should back `kagent-tool-server`. The server manifest and service should
remain separate from the sample A2A agent manifest.
