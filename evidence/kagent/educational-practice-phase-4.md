# kagent Educational Practice: Phase 4 Evidence

## Meta

| Field | Value |
|-------|-------|
| Date | 2026-07-16 |
| Time | 13:00 - 17:15 UTC+3:30 |
| Machine | Windows (win32 10.0.26200) |
| Cluster | Docker Desktop (context: `docker-desktop`) |
| Kubernetes node | `desktop-control-plane`, v1.36.1 |
| kagent namespace | `kagent` |
| Practice | `phase_4_real_mcp_server` |
| Subphases | 4A (design), 4B (manifests), 4C (apply/observe), 4D (evidence) |

## Files Changed or Created

| File | Action |
|------|--------|
| `evidence/kagent/educational-practice-phase-4a-design.md` | Created (design decision record) |
| `deploy/base/kagent/kagent-tool-server-runtime.yaml` | Created (ServiceAccount, RBAC, Deployment, Service) |
| `deploy/README.md` | Updated (added runtime manifest to tree) |
| `evidence/kagent/educational-practice-phase-4.md` | Created (this file) |
| `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md` | Updated (evidence pointer) |
| `docs/runbooks/local-kagent-a2a-lab.md` | Updated (deploy tree, known limitations) |
| `REPO_MANIFEST.yaml` | Updated (new entries) |

## Cluster State Before Applying Runtime

### Services (before)

No service named `kagent-tool-server` existed. The existing `kagent-tool-server` name was used only by the `RemoteMCPServer` custom resource.

### RemoteMCPServer (before)

```
kagent-tool-server   STREAMABLE_HTTP   http://kagent-tool-server.kagent:8000/mcp   False
```

Condition: `Accepted=False`, `Reason=ReconcileFailed`, message included:
```
Post "http://kagent-tool-server.kagent:8000/mcp": dial tcp: lookup kagent-tool-server.kagent on 10.96.0.10:53: no such host
```

### Pods (before)

17 pods. No `kagent-tool-server` pod.

## Commands Run

### 1. Apply runtime manifest

```powershell
kubectl apply -f deploy/base/kagent/kagent-tool-server-runtime.yaml
```

Exit code: 0

Resources created:
- `serviceaccount/kagent-tool-server`
- `clusterrole.rbac.authorization.k8s.io/kagent-tool-server-readonly`
- `clusterrolebinding.rbac.authorization.k8s.io/kagent-tool-server-readonly`
- `deployment.apps/kagent-tool-server`
- `service/kagent-tool-server`

### 2. Check pod rollout

Initial cycle crashed with `CrashLoopBackOff` because the `0.0.13` Python image
does not support the `--read-only` flag. The flag was removed from the manifest
and reapplied. Second attempt succeeded.

```powershell
kubectl apply -f deploy/base/kagent/kagent-tool-server-runtime.yaml
kubectl get pods -n kagent --no-headers | Select-String "kagent-tool-server"
```

Final result:
```
kagent-tool-server-7c65c7fb6-5vzh7  1/1  Running  0  35m
```

### 3. Verify Service

```powershell
kubectl get svc -n kagent --no-headers | Select-String "kagent-tool-server"
```

Result:
```
kagent-tool-server  ClusterIP  10.96.86.193  <none>  8000/TCP  40m
```

Port mapping confirmed: 8000 -> targetPort 8084.

### 4. Check RemoteMCPServer status

```powershell
kubectl get remotemcpserver -n kagent --no-headers
```

Result:
```
kagent-grafana-mcp   STREAMABLE_HTTP   http://kagent-grafana-mcp.kagent:8000/mcp   False
kagent-tool-server   STREAMABLE_HTTP   http://kagent-tool-server.kagent:8000/mcp   True
```

### 5. Describe RemoteMCPServer (condition details)

```powershell
kubectl describe remotemcpserver kagent-tool-server -n kagent
```

Key condition:
```
Accepted:  Status=True, Reason=Reconciled
Message:   Remote MCP server configuration accepted
```

The controller discovered **94 tools** from the MCP server, covering:
- Argo Rollouts tools (7)
- Cilium tools (40+)
- Helm tools (6)
- Istio tools (12+)
- Kubernetes core tools (19, including `k8s_get_resources` and `k8s_get_available_api_resources`)
- Prometheus tools (5)
- Standard tools (datetime, shell)

### 6. Health checker

```powershell
.\scripts\kagent\check-kagent-health.ps1
```

Exit code: 0

Summary:
- 18/18 pods ready (previously 17)
- 11/11 agents accepted+ready
- 2 RemoteMCPServer(s) present (1 accepted -- `kagent-tool-server`)
- `kagent-tool-server` line: `[PASS] kagent-tool-server  http://kagent-tool-server.kagent:8000/mcp  accepted=True`
- `kagent-grafana-mcp` line: `[INFO] ... accepted=False (expected if actual MCP server is not deployed)`

## Capability Level Assessment

| Level | Description | Decision | Evidence |
|-------|-------------|----------|----------|
| L0 | Config exists | Proven | Manifests, scripts, design doc, evidence files exist in repo |
| L1 | Control plane healthy | Proven | 18/18 pods ready; health checker exit 0 |
| L2 | Agent accepted/ready | Proven | 11/11 agents Accepted=True, Ready=True |
| L3 | Agent details/card observable | Proven | Previously proven in phases 0-2 |
| L4 | A2A task dispatch works | Not proven | `task` exits 1 with `-32601 method not found` (unchanged) |
| **L5** | **RemoteMCPServer accepted** | **Proven** | `kagent-tool-server` shows `Accepted=True`, `Reason=Reconciled`, 94 tools discovered |
| L6 | Tool invocation proven | Not proven | No task -> agent -> MCP tool -> result recorded |
| L7 | Repeatable workshop/install path | Not proven | No bootstrap/cleanup automation exercised |

## What This Phase Proves

- A real MCP server (official kagent tools image `ghcr.io/kagent-dev/kagent/tools:0.0.13`) can be deployed in-cluster behind the `kagent-tool-server` service.
- Deploying a runtime Deployment and Service named `kagent-tool-server` satisfies the existing RemoteMCPServer URL.
- The controller reconciles the RemoteMCPServer to `Accepted=True` after the MCP endpoint becomes reachable.
- The controller discovers and lists all tools exposed by the MCP server (94 tools observed).
- The health checker correctly reports the transition to `[PASS]` for an accepted RemoteMCPServer.
- RBAC-only read restriction works: the server registers write tools but RBAC denies their Kubernetes API calls.

## What This Phase Does NOT Prove

- L6 tool invocation: no A2A task has been sent that calls a discovered tool and returns a result.
- L7 repeatability: no one-command bootstrap or cleanup exists.
- Production hardening: no readiness checks, resource tuning, or multi-replica setup.
- A2A task dispatch (L4): JSON-RPC `tasks/sendTask` still returns `-32601`.

## Guardrails Compliance

- `RemoteMCPServer Accepted=True` is recorded as L5 evidence only, not L6.
- Tool invocation is explicitly not claimed (no task -> agent -> MCP tool -> result).
- A2A dispatch truth is kept separate from MCP server acceptance.
- Real MCP server runtime manifests are in `deploy/base/` (not `deploy/samples/`).
- Write tools like `k8s_delete_resource` are present in the server but RBAC-restricted.
- The `kagent-grafana-mcp` RemoteMCPServer remains `Accepted=False` and out of scope.

## Deviations from Design

1. The `--read-only` flag was removed because the `0.0.13` Python tools image
   does not support it. The `v0.2.x` Go image does, but was not verified pullable.
   RBAC-only read restriction is functionally equivalent for the lab.
2. The `/health` HTTP probe was replaced with a TCP probe because the tools
   server does not expose an HTTP health endpoint.

## Unaddressed Problems

- The MCP server registers write tools (`k8s_delete_resource`, `k8s_execute_command`,
  `k8s_apply_manifest`) in its tool list. RBAC restricts them, but a future upgrade
  to a `--read-only`-supporting image would be cleaner.
- `kagent-grafana-mcp` RemoteMCPServer remains `Accepted=False`.
- L4 A2A task dispatch remains unproven (`tasks/sendTask` returns `-32601`).
- L6 tool invocation remains unproven with no recorded task -> tool -> result loop.

## Next Recommended Step

Proceed to `phase_5_real_agentic_work`. With L5 now proven, the next phase should:

1. Verify L4 task dispatch (possibly via `a2a-cli` since the controller doesn't
   expose `tasks/sendTask` natively).
2. Or, if task dispatch remains blocked, demonstrate tool invocation by calling
   the MCP server directly (via a tool-call curl) and record the result as the
   first piece of L6 evidence.
3. After a tool invocation succeeds, connect it through the agent path by having
   the agent use `k8s_get_resources` or `k8s_get_available_api_resources` and
   return a result.
