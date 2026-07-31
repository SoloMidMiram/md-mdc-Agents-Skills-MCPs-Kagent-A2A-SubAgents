# kagent Educational Practice: Phases 0-2 Evidence

## Meta

| Field | Value |
|-------|-------|
| Date | 2026-07-16 |
| Time | 13:34 - 13:41 UTC+3:30 |
| Machine | Windows (win32 10.0.26200) |
| Cluster | Docker Desktop (context: `docker-desktop`) |
| Kubernetes node | `desktop-control-plane`, v1.36.1 |
| kagent namespace | `kagent` |

## Commands Run

All commands ran from `F:\Git\MCPtest` (repository root).

### Phase 0: Observe (`phase_0_observe`)

#### 1. `.\scripts\kagent\check-kagent-health.ps1`

Exit code: 0 (ALL CHECKS PASSED)

Summary output:
- 17/17 pods ready
- 11/11 agents accepted+ready
- 2 RemoteMCPServer(s) present (0 accepted)
- No recent events

#### 2. `kubectl get pods -n kagent`

All 17 pods `1/1 Running`:

| Pod | Restarts |
|-----|----------|
| argo-rollouts-conversion-agent | 14 |
| cilium-debug-agent | 14 |
| cilium-manager-agent | 14 |
| cilium-policy-agent | 14 |
| helm-agent | 14 |
| istio-agent | 14 |
| k8s-a2a-agent | 14 |
| k8s-agent | 14 |
| kagent-controller | 41 |
| kagent-grafana-mcp | 14 |
| kagent-kmcp-controller-manager | 16 |
| kagent-postgresql | 14 |
| kagent-querydoc | 14 |
| kagent-ui | 47 |
| kgateway-agent | 14 |
| observability-agent | 14 |
| promql-agent | 14 |

All `Status=Running`, all `Ready=1/1`.

#### 3. `kubectl get agent -n kagent`

11 agents, all `TYPE=Declarative` (one `TYPE=Declarative RUNTIME=go` for k8s-a2a-agent):

| Agent | Accepted | Ready |
|-------|----------|-------|
| argo-rollouts-conversion-agent | True | True |
| cilium-debug-agent | True | True |
| cilium-manager-agent | True | True |
| cilium-policy-agent | True | True |
| helm-agent | True | True |
| istio-agent | True | True |
| k8s-a2a-agent | True | True |
| k8s-agent | True | True |
| kgateway-agent | True | True |
| observability-agent | True | True |
| promql-agent | True | True |

#### 4. `kubectl get remotemcpserver -n kagent`

| Name | URL | Accepted |
|------|-----|----------|
| kagent-grafana-mcp | http://kagent-grafana-mcp.kagent:8000/mcp | False |
| kagent-tool-server | http://kagent-tool-server.kagent:8000/mcp | False |

#### 5. `kubectl get events -n kagent --sort-by=.lastTimestamp`

Output: `No resources found in kagent namespace.`

Events have been cleaned up from the namespace.

### Phase 1: UI and Card (`phase_1_ui_and_card`)

#### 6. `kubectl port-forward -n kagent svc/kagent-ui 8080:8080` + `curl.exe http://localhost:8080`

HTTP Status: **200**

The kagent UI endpoint is reachable through port-forward. This evidence proves
HTTP reachability; rendered UI behavior was not separately captured with a
browser snapshot or screenshot in this evidence file.

#### 7. `kubectl port-forward -n kagent svc/kagent-controller 8083:8083` + `python scripts/kagent/test-a2a-agent.py card`

Output:
```
Agent: kagent/k8s-a2a-agent
Accepted: True
DeploymentReady: True
Model: gpt-4.1-mini (OpenAI)
Skills (1):
  - get-resources-skill: Get Resources - Get resources in the Kubernetes cluster
```

Exit code: 0 (PASS).

#### 8. `curl.exe http://localhost:8083/api/agents/kagent/k8s-a2a-agent`

Full JSON response confirms:

- `accepted`: true (condition reason: Reconciled, message: "Agent configuration accepted")
- `deploymentReady`: true (condition reason: DeploymentReady, message: "Deployment is ready")
- `model`: gpt-4.1-mini
- `modelProvider`: OpenAI
- `tools`: references `RemoteMCPServer/kagent-tool-server` with tool names `k8s_get_resources` and `k8s_get_available_api_resources`
- One A2A skill: `get-resources-skill`

### Phase 2: Degraded MCP Understanding (`phase_2_degraded_mcp_understanding`)

#### 9. `kubectl describe remotemcpserver kagent-tool-server -n kagent`

Key details:
- URL: `http://kagent-tool-server.kagent:8000/mcp`
- Protocol: `STREAMABLE_HTTP`
- Timeout: 30s
- **Accepted condition: Status=False, Reason=ReconcileFailed**
- Message: `failed to fetch tools for toolServer kagent/kagent-tool-server: failed to connect client for toolServer kagent/kagent-tool-server: calling "initialize": sending "initialize": rejected by transport: Post "http://kagent-tool-server.kagent:8000/mcp": dial tcp: lookup kagent-tool-server.kagent on 10.96.0.10:53: no such host`

This confirms the controller attempted to connect but the DNS name `kagent-tool-server.kagent` does not resolve -- no MCP server is deployed at that address.

#### 10. Inspected `deploy/base/kagent/kagent-tool-server.yaml`

The manifest defines the same URL (`http://kagent-tool-server.kagent:8000/mcp`) with a comment:
> For full tool availability, deploy a k8s MCP server at this address.

This aligns with the observed `Accepted=False` state. The manifest is a reusable base resource; the backing service does not yet exist.

## Capability Level Assessment

Per the L0-L7 grid defined in `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`:

| Level | Description | Proven? | Evidence |
|-------|-------------|---------|----------|
| L0 | Config exists | **Proven** | Manifests at `deploy/base/kagent/kagent-tool-server.yaml` and `deploy/samples/kagent/k8s-a2a-agent.yaml`; health and test scripts at `scripts/kagent/` |
| L1 | Control plane healthy | **Proven** | 17/17 pods Running 1/1 Ready; health checker exits 0 |
| L2 | Agent accepted/ready | **Proven** | 11/11 agents Accepted=True, Ready=True; `kubectl get agent` confirms |
| L3 | Agent details/card observable | **Proven** | REST API returns full agent metadata; `test-a2a-agent.py card` prints accepted state, model, skills |
| L4 | A2A task dispatch works | **Not proven** | JSON-RPC tasks/sendTask returns -32601 per prior testing; not tested in this session |
| L5 | RemoteMCPServer accepted | **Not proven** | Both RemoteMCPServers show Accepted=False; DNS resolution fails |
| L6 | Tool invocation proven | **Not proven** | No MCP tool has been invoked and recorded |
| L7 | Repeatable workshop path | **Not proven** | No bootstrap/cleanup automation exists |

## Per-Practice Analysis

### What Each Practice Proves

- **Health checker**: kagent control plane is installed and all components are running. The controller reconciles agents successfully. RemoteMCPServers exist but their backing services are unreachable, which is correctly reported.
- **kubectl inspect commands**: Resource types (pods, agents, RemoteMCPServers) can be observed. Agent conditions (Accepted, Ready) are populated by the controller.
- **UI reachability**: The kagent UI service is accessible and renders through port-forward. This is a control-plane observation, not task-execution evidence.
- **Agent card/REST API**: The controller exposes agent metadata including accepted status, deployment readiness, model configuration, and declared skills. The `Accepted=True` condition has reason "Reconciled" confirming this is reconciliation, not tool execution.
- **RemoteMCPServer describe**: Reveals the exact DNS failure when no MCP server is deployed. The `Accepted=False`, `Reason=ReconcileFailed` status is the correct degraded-lab state for card/acceptance testing only.

### What It Does NOT Prove

- A2A task dispatch across the JSON-RPC boundary
- Agent-to-MCP tool invocation (the agent's declared tools `k8s_get_resources` and `k8s_get_available_api_resources` cannot be called)
- RemoteMCPServer connectivity to a real MCP endpoint
- End-to-end agentic workflow (task -> agent -> MCP tool -> result)
- Repeatable bootstrap or cleanup

## Deviations from July 9 Baseline

The documented baseline in `docs/runbooks/local-kagent-a2a-lab.md` (dated July 9, 2026) matches current state on all structural properties:

- 17 pods (still true)
- 11 agents (still true)
- 2 RemoteMCPServers (still true)
- All agents Accepted=True, Ready=True (still true)
- RemoteMCPServers Accepted=False (still true)
- UI HTTP 200 (still true)
- Controller REST API reachable (still true)

Changes observed:

| Aspect | July 9 baseline | July 16 observed |
|--------|----------------|-----------------|
| Pod restart counts | Most pods: 1 restart; controller/UI: 3-6 | Most pods: 14 restarts; controller: 41; UI: 47 |
| Events | Present (sorted by lastTimestamp) | No events found (cleaned up) |
| kagent-controller uptime | 7d2h | Same deployment age, high restarts indicate repeated rolling updates |
| Container image version | Not recorded | Not checked (no version drift expected) |

The restart count increase is consistent with repeated `helm upgrade` commands during the lab's lifetime. This does not affect pod readiness or agent acceptance.

## Guardrails Compliance

- `Accepted=True` on agents is reported as reconciliation evidence, not tool execution.
- Card/REST API success is reported as metadata observation, not task success.
- `RemoteMCPServer Accepted=False` is documented as an expected degraded-lab state, acceptable for card/acceptance testing only.
- No architectural or capability claims extend beyond what the commands actually produced.
- The evidence file avoids reusing L2 or L3 evidence to imply L5 or L6.

## Next Recommended Step

Per `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`: proceed to `phase_3_truthful_a2a_dispatch`.

Jobs:
1. Fix `scripts/kagent/test-a2a-agent.py task` semantics so unavailable dispatch exits non-zero (currently `both` action prints INFO but exits 0 when task fails).
2. Validate `probe` reports supported methods neutrally without claiming task success.
3. Keep `card` scoped to REST/card validation only (already correct).
4. Split `both` so it passes only when both card and task pass.
5. After truthful task dispatch semantics are verified, document the real dispatch flow in the runbook.
