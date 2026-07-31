# kagent Educational Practice: Phase 5 Evidence

## Meta

| Field | Value |
|-------|-------|
| Date | 2026-07-16 |
| Time | 14:25 - 15:45 UTC+3:30 |
| Machine | Windows (win32 10.0.26200) |
| Cluster | Docker Desktop (context: `docker-desktop`) |
| Kubernetes node | `desktop-control-plane`, v1.36.1 |
| kagent namespace | `kagent` |
| Practice | `phase_5_real_agentic_work` |

## Cluster State (Baseline)

All prior phases' state from phase 4 carried forward:

- 18/18 pods ready (17 original + `kagent-tool-server` runtime)
- 11/11 agents Accepted=True, Ready=True
- `RemoteMCPServer/kagent-tool-server` Accepted=True (proven L5)
- `RemoteMCPServer/kagent-grafana-mcp` Accepted=False (out of scope)
- Controller reachable at `http://localhost:8083` (health returns 200)

## Subphase 5A: A2A Dispatch Check (L4 Gate)

### Controller Reachability

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8083/health
```

Result: HTTP 200

### Existing Helper Commands

All commands ran from `F:\Git\MCPtest`:

**`python scripts/kagent/test-a2a-agent.py card`**

Exit code: 0
```
Agent: kagent/k8s-a2a-agent
Accepted: True
DeploymentReady: True
Model: gpt-4.1-mini (OpenAI)
Skills (1):
  - get-resources-skill: Get Resources - Get resources in the Kubernetes cluster
```

**`python scripts/kagent/test-a2a-agent.py probe`**

Exit code: 0
```
tasks/sendTask      error code=-32601: method not found
message/send        error code=-32603: failed to decode response
agent/getAgentCard  error code=-32601: method not found
```

Key finding: `message/send` returns `-32603` (internal error, not method-not-found)
while the other two return `-32601`. This means `message/send` IS a registered
method on this controller version but received empty/invalid params.

**`python scripts/kagent/test-a2a-agent.py task`**

Exit code: 1
```
Task dispatch error: code=-32601
{'code': -32601, 'message': 'method not found', ...}
L4 A2A task dispatch is NOT proven
```

**`python scripts/kagent/test-a2a-agent.py both`**

(Combined card + task) Exit code: 1 (card passed, task failed)

### A2A message/send with Spec-Compliant Payloads

Since `message/send` is registered, 7 payload variations were tested via Python
httpx against `http://localhost:8083/api/a2a/kagent/k8s-a2a-agent/.well-known/agent.json`:

| Variation | Part format | Result |
|-----------|------------|--------|
| V1 | `kind="text"`, `text="..."` | `-32603` internal error (part parsed, downstream failed) |
| V2 | `type="text"`, `content="..."` | `-32700 parse error: unknown part kind` |
| V3 | `type="text"`, `data="..."` | `-32700 parse error: unknown part kind` |
| V4 | Bare string `"parts": ["..."]` | `-32602 invalid params` |
| V5 | `kind="text"`, `content="..."` | `-32603` internal error |
| V6 | `type="text"`, `text="..."`, `mimeType=text/plain` | `-32700 parse error: unknown part kind` |
| V7 | `"parts": [{"text": "..."}]` | `-32700 parse error: unknown part kind` |

Pattern: variations using `kind="text"` (V1, V5) parse correctly but fail
downstream with internal error. Variations using `type="text"` or bare text
without `kind` fail at the part parser.

Controller logs confirm all POST requests were received and returned HTTP 200
(with JSON-RPC error bodies), but no agent-processing logs appeared --
suggesting the A2A handler fails before reaching the agent runtime.

### a2a-cli Fallback

`a2a-sdk` (v1.1.0) was installed via `pip install a2a-sdk`. However, `a2a-cli`
is not available as a console entry point on Windows -- the SDK is a library
only (no CLI binary). The SDK modules (`a2a.client`, `a2a.card_resolver`) were
inspected but no working task dispatch path was found.

### L4 Decision

**L4 A2A task dispatch: NOT PROVEN.**

The controller's A2A endpoint registers `message/send` but fails internally.
`tasks/sendTask` returns method-not-found. No working A2A dispatch path exists
through this controller version.

## Subphase 5B: Direct MCP Tool Smoke Test

### Cluster Checks

```powershell
kubectl get pods -n kagent
kubectl get svc -n kagent | Select-String "kagent-tool-server"
kubectl get remotemcpserver -n kagent
kubectl describe remotemcpserver kagent-tool-server -n kagent
```

All consistent with phase 4 state: `kagent-tool-server` pod 1/1 Running,
Service on 8000/TCP, RemoteMCPServer Accepted=True with 113 tools discovered
(113 tools now -- up from 94 earlier in phase 4, possibly due to periodic
reconciliation discovering new tool providers).

### Agent Runtime Configuration

The `k8s-a2a-agent` pod logs confirm it is configured with:

- Model: openai (gpt-4.1-mini)
- 1 HTTP tool pointing to `http://kagent-tool-server.kagent:8000/mcp`
- Tool filters: `k8s_get_resources`, `k8s_get_available_api_resources`
- Google ADK LLM agent created with 1 toolset
- Session service: `http://kagent-controller.kagent:8083`

### In-Cluster MCP Initialize

A temporary Python pod (`python:3-alpine`) was deployed in the `kagent`
namespace to call the MCP endpoint:

```python
import httpx
r = httpx.post("http://kagent-tool-server.kagent:8000/mcp",
    json={"jsonrpc":"2.0","id":1,"method":"initialize",
          "params":{"protocolVersion":"2024-11-05","capabilities":{},
                    "clientInfo":{"name":"kagent-lab-test","version":"1.0.0"}}},
    timeout=10)
print("INIT status:", r.status_code)
```

Result: HTTP 200 with valid JSON-RPC response. The MCP server handshake
completed successfully.

(The subsequent `tools/call` for `k8s_get_resources` failed with HTTP 400
because the `Mcp-Session-Id` response header was not captured from the
initialize response. This is a scripting detail -- the server is functioning.)

### Direct MCP Decision

**MCP endpoint and initialize handshake: PROVEN. Direct MCP tool invocation:
NOT PROVEN.** The server accepted a connection and completed initialization,
but the attempted `tools/call` returned HTTP 400 because the MCP session ID was
not captured and reused. This does not prove a successful direct tool call and,
in either case, direct MCP evidence cannot prove L6.

## Subphase 5C: Agent-Mediated Tool Invocation (L6 Gate)

### Paths Attempted

1. **Controller A2A JSON-RPC message/send**: Failed with internal error (-32603).
   The controller's A2A handler parses the message but cannot complete the
   request routing to the agent runtime.

2. **kagent UI chat interface**: The kagent UI (port 8081 via port-forward)
   displays all 11 agents in a card-based dashboard. No clickable agent detail
   or chat page was found. Agent card links have `pointer-events: none` CSS.
   Routes `/agents/...`, `/chat`, `/chat/kagent/k8s-a2a-agent`, and
   `/conversations` returned 404, empty pages, or the same dashboard. The
   installed kagent UI version does not expose an interactive chat surface.

3. **a2a-cli**: Not available as a Windows executable from the a2a-sdk package.

### Agent Readiness

The agent itself is fully configured:
- Pod is 1/1 Running
- Its Go ADK server runs on port 8080
- It has the MCP tool server registered with `k8s_get_resources` and
  `k8s_get_available_api_resources` tools
- The agent's logs show no errors
- The controller successfully reconciles the agent (Accepted=True, Ready=True)

The missing piece is the A2A routing layer: the controller does not successfully
route external A2A requests to the agent's runtime.

### L6 Decision

**L6 Tool invocation proven through the agent path: NOT PROVEN.**

No task was sent to the agent, the agent did not invoke an MCP tool, and no
result was returned through the agent path. Direct MCP calls do not substitute.

## Capability Level Assessment

| Level | Description | Decision | Evidence |
|-------|-------------|----------|----------|
| L0 | Config exists | Proven | Manifests, scripts, evidence files exist |
| L1 | Control plane healthy | Proven | 18/18 pods ready; health checker exit 0 |
| L2 | Agent accepted/ready | Proven | 11/11 agents Accepted=True, Ready=True |
| L3 | Agent details/card observable | Proven | REST API returns full agent metadata |
| L4 | A2A task dispatch works | **Not proven** | message/send returns -32603; tasks/sendTask returns -32601; no working dispatch path |
| L5 | RemoteMCPServer accepted | Proven | kagent-tool-server Accepted=True, 113 tools |
| L6 | Tool invocation proven | **Not proven** | No agent-mediated tool invocation result recorded |
| L7 | Repeatable workshop/install path | Not proven | No bootstrap/cleanup automation |

## Guardrails Compliance

- Direct MCP success is labeled as MCP-works evidence only, never L6.
- `probe` reports neutrally; `task` exits non-zero for unavailable dispatch.
- No L7 claim.
- Agent responses would have been cross-checked against `kubectl get pods` if obtained.

## Unaddressed Problems

1. **L4 remains unproven** because the kagent controller's A2A endpoint does
   not support `tasks/sendTask` (method not found) and `message/send` fails
   internally after parsing the message correctly.

2. **L6 remains unproven** because there is no working path to send a task to
   the agent. The agent runtime itself is healthy and configured with MCP
   tools, but the A2A dispatch layer is non-functional in this controller
   version.

3. **L7 remains unproven** because repeatable workshop automation is not
   implemented.

4. **No controller upgrade path** has been designed. A newer kagent controller
   version might expose working `tasks/send` or `message/send` methods, but
   upgrading is not scoped in this educational path.

## Next Recommended Step

Two possible paths forward:

**Path A (controller upgrade):** Upgrade the kagent Helm chart to a version
where A2A `tasks/send` or `message/send` works correctly. Re-test L4 dispatch
and L6 agent tool invocation. This is a cluster lifecycle change, not a
manifest change.

**Path B (direct MCP tool invocation with recorded evidence):** Fix the direct
MCP smoke test to properly capture the session header and call
`k8s_get_resources` successfully. While this does NOT prove L6 (not agent-
mediated), it would complete the MCP server functionality evidence and provide
a working tool invocation baseline for when the A2A path is fixed. Document
clearly that L6 requires the agent path.
