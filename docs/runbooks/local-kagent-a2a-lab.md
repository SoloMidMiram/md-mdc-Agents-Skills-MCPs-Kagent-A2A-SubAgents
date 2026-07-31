# Local kagent + A2A Lab

This runbook is the shortest path from a local Kubernetes cluster to a working
kagent A2A lab: deploy, reconcile, verify, and inspect the sample A2A agent.

For the phase-by-phase learning path and architecture guardrails, read
[kagent Educational Roadmap](../onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
before using this runbook.

## Lab Status Summary

As of July 17, 2026 the local kagent lab is in the following state:

- **Infrastructure:** 18/18 pods Running and Ready; 11/11 agents Accepted=True Ready=True.
- **REST agent card:** Reachable and returns full agent metadata (works).
- **A2A `message/stream`:** Proven for L4 via structured helper JSON (phase 5d).
- **JSON-RPC `tasks/sendTask`:** Not exposed (`-32601`); empty-param probes may still error.
- **RemoteMCPServer:** `kagent-tool-server` is `Accepted=True` (real MCP server deployed). `kagent-grafana-mcp` remains `Accepted=False` (no backing service).
- **UI:** Reachable at `http://localhost:8080` (returns HTTP 200).
- **Controller API:** Reachable at `http://localhost:8083`.
- **L6:** Not proven ([phase 5e](../../evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md)).

## Current Local State

Observed on this machine through July 17, 2026:

- Docker Desktop cluster (context: `docker-desktop`).
- All 18 kagent pods are `Running` with complete readiness ratios (17 original
  pods + `kagent-tool-server` runtime).
- All agents including `k8s-a2a-agent` show `Accepted=True` and `Ready=True`.
- `kagent-tool-server` RemoteMCPServer is `Accepted=True` -- a real MCP server (official kagent tools image) is deployed behind the service URL.
- `kagent-grafana-mcp` RemoteMCPServer shows `Accepted=False` because no MCP server is deployed at its URL.
- UI is reachable on `http://localhost:8080` via port-forward.
- Controller REST API is reachable on `http://localhost:8083`.
- `kagent-openai` secret is required for agents and must be created separately.

## Prerequisites

| Tool       | Required | Check command                     |
|------------|----------|-----------------------------------|
| Docker     | Yes      | `docker info`                     |
| kubectl    | Yes      | `kubectl config current-context`  |
| Helm       | Yes      | `helm version`                    |
| Python 3   | For test | `python --version`                |

Ensure the context is `docker-desktop`:

```powershell
kubectl config current-context
```

## Quick-Start (Full Install)

### 1. Create namespace

```powershell
kubectl create namespace kagent --dry-run=client -o yaml | kubectl apply -f -
```

### 2. Install CRDs

```powershell
helm upgrade --install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds `
  --namespace kagent
```

### 3. Set the API key

```powershell
$env:OPENAI_API_KEY = "<your-api-key>"
```

### 4. Install kagent core

```powershell
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent `
  --namespace kagent `
  --set providers.default=openAI `
  --set providers.openAI.apiKey=$env:OPENAI_API_KEY
```

### 5. Create the `kagent-openai` secret

Helm may not create the secret automatically. If any agent pods show
`CreateContainerConfigError`, create the secret:

```powershell
kubectl create secret generic kagent-openai `
  --from-literal=OPENAI_API_KEY=$env:OPENAI_API_KEY `
  -n kagent
```

### 6. Wait for workloads

```powershell
kubectl get pods -n kagent -w
```

Every pod should be `Running` with a complete positive readiness ratio such as
`1/1` or `2/2`.

## Reconcile (if already installed)

Run these to ensure everything is current:

```powershell
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent `
  --namespace kagent `
  --set providers.default=openAI `
  --set providers.openAI.apiKey=$env:OPENAI_API_KEY
```

Then ensure the secret exists:

```powershell
kubectl get secret kagent-openai -n kagent
```

If missing, create it as shown in step 5 above.

## Apply Sample A2A Resources

The lab uses three resources applied in order:

1. **`kagent-tool-server`** (`RemoteMCPServer`) - base resource shared by multiple agents
2. **`kagent-tool-server-runtime`** (Deployment + Service + RBAC) - MCP server runtime that backs the RemoteMCPServer URL
3. **`k8s-a2a-agent`** (`Agent`) - sample A2A agent for read-only cluster inspection

Apply them in order:

```powershell
kubectl apply -f deploy/base/kagent/kagent-tool-server.yaml
kubectl apply -f deploy/base/kagent/kagent-tool-server-runtime.yaml
kubectl apply -f deploy/samples/kagent/k8s-a2a-agent.yaml
```

Wait for the tool server pod to become ready:

```powershell
kubectl wait --for=condition=Ready pod -n kagent -l app.kubernetes.io/component=tool-server-runtime --timeout=120s
```

Resources are organized as:

```
deploy/
  base/kagent/
    kagent-tool-server.yaml           # shared MCP server reference (RemoteMCPServer CR)
    kagent-tool-server-runtime.yaml   # MCP server runtime (Deployment + Service + RBAC)
  samples/kagent/
    k8s-a2a-agent.yaml                # sample A2A agent (educational / lab use)
```

## Verify Health

### Quick health check

```powershell
.\scripts\kagent\check-kagent-health.ps1
```

This inspects:
- pod readiness (all pods Running with complete positive ratios such as `1/1` or `2/2`)
- agent status (Accepted=True, Ready=True)
- RemoteMCPServer status
- recent events
- service endpoint hints for port-forward

### Manual inspection commands

```powershell
# Pod health
kubectl get pods -n kagent
kubectl describe pod -n kagent <pod-name>

# Agent health
kubectl get agent -n kagent
kubectl describe agent k8s-a2a-agent -n kagent

# RemoteMCPServer health
kubectl get remotemcpserver -n kagent
kubectl describe remotemcpserver kagent-tool-server -n kagent

# Events
kubectl get events -n kagent --sort-by=.lastTimestamp

# Logs (key pods)
kubectl logs -n kagent deployment/kagent-controller --tail=50
kubectl logs -n kagent deployment/kagent-ui --tail=50
```

## Open the kagent UI

```powershell
# Terminal 1: UI (port 8080)
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```

Then open `http://localhost:8080`.

## Test A2A

### Terminal 2: Controller port-forward

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
```

### Run the A2A test script

```powershell
# Fetch the agent card (shows accepted/ready state, model, skills)
python scripts/kagent/test-a2a-agent.py card

# Full test: card + task dispatch attempt
python scripts/kagent/test-a2a-agent.py both

# Probe available A2A JSON-RPC methods
python scripts/kagent/test-a2a-agent.py probe

# Inspect the kagent REST API directly
curl.exe http://localhost:8083/api/agents/kagent/k8s-a2a-agent
```

Expected output from `card`:
```
Agent: kagent/k8s-a2a-agent
Accepted: True
DeploymentReady: True
Model: gpt-4.1-mini (OpenAI)
Skills (1):
  - get-resources-skill: Get Resources - Get resources in the Kubernetes cluster
```

### A2A client compatibility note

The current controller does not expose legacy `tasks/sendTask`, and the tested
blocking `message/send` path fails internally. Controller 0.9.11's working L4
path is the same path used by the UI: `message/stream` over SSE with a complete
`MessageSendParams` text message. The repository helper implements and strictly
validates that path; no external `a2a-cli` installation is recommended.

The REST API agent card fetch works reliably and verifies that the agent is
accepted, ready, and configured with the correct skills.

The helper uses truthful exit codes:

- `card` exits 0 when agent metadata/card details are reachable.
- `probe` exits 0 when method probing completes, even if methods are unsupported.
- `task` exits 0 only after a valid `message/stream` response contains a
  non-empty task/message id in an accepted state.
- `both` exits 0 only when both card validation and task dispatch pass.

With a controller port-forward, the recorded Phase 5D `task` and `both` paths
pass L4. A later terminal model failure does not revoke L4 after an accepted
state was observed; it still does not prove L6.

### Verify the native controller MCP surface

The project-scoped Cursor and Codex configurations both target the discovered
controller endpoint. This is the normal IDE-facing seam; the A2A commands above
remain protocol and evidence diagnostics.

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
python scripts/kagent/controller_mcp_smoke.py --output json
```

Expected success behavior: the helper exits `0` after `initialize`,
`tools/list`, `list_agents`, a bounded `invoke_agent` response, and a
same-session continuation. It records only whether the MCP session was present,
never its value. Exit `1` means the controller contract or bounded agent result
did not qualify; exit `3` means the endpoint was unavailable. Neither result
proves L6. The recorded Phase 6 observation currently proves I0-I2 and marks I3
Blocked because the configured provider rejects the local region.

## How to Observe Failures

### Agent not Accepted

```powershell
kubectl describe agent k8s-a2a-agent -n kagent
```

Common causes:
- Missing `RemoteMCPServer`: `kubectl get remotemcpserver -n kagent`
- Missing secret: `kubectl get secret -n kagent`
- Controller logs: `kubectl logs -n kagent deployment/kagent-controller --tail=50`

### Pod not Running

```powershell
kubectl describe pod -n kagent <pod-name>
kubectl logs -n kagent <pod-name> --tail=50
kubectl get events -n kagent --sort-by=.lastTimestamp
```

Common causes:
- `CreateContainerConfigError`: missing secret or ConfigMap
- `ImagePullBackOff`: image not accessible
- `CrashLoopBackOff`: inspect logs for application errors

### Health check script

```powershell
.\scripts\kagent\check-kagent-health.ps1
```

Default remains CardLab (pods + accepted/ready agents). Named profiles make
capability claims explicit — see
[kagent health profiles](../reference/kagent-health-profiles.md).

```powershell
.\scripts\kagent\check-kagent-health.ps1 -Profile CardLab
.\scripts\kagent\check-kagent-health.ps1 -Profile DirectMcpServer -DirectMcpResultPath <sanitized-json> -OutputFormat Json
.\scripts\kagent\check-kagent-health.ps1 -Profile A2ADispatch -ControllerUrl http://127.0.0.1:8083
.\scripts\kagent\check-kagent-health.ps1 -Profile FullMcpExecution -ControllerUrl http://127.0.0.1:8083
.\scripts\kagent\check-kagent-health.ps1 -Profile FullMcpExecution -ControllerUrl http://127.0.0.1:8083 -AgentToolEvidencePath <agent-mediated-json>

# FullMcpExecution uses the canonical target by default
.\scripts\kagent\check-kagent-health.ps1 `
  -Profile FullMcpExecution `
  -ControllerUrl http://127.0.0.1:8083
```

On the current lab, expect CardLab, DirectMcpServer, and A2ADispatch to pass
when the controller port-forward is up and the A2A helper can complete
`message/stream`. FullMcpExecution still fails until a live correlated L6
record exists ([phase 5e](../../evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md)).
Omitting `-AgentToolEvidencePath` invokes `agent_mcp_trace.py --output json`.

### Trustworthy A2A helper

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
python scripts/kagent/test-a2a-agent.py card --controller http://127.0.0.1:8083 --output json
python scripts/kagent/test-a2a-agent.py probe --controller http://127.0.0.1:8083 --output json
python scripts/kagent/test-a2a-agent.py task --controller http://127.0.0.1:8083 --output json
python scripts/kagent/test-a2a-agent.py both --controller http://127.0.0.1:8083 --output json
```

Pinned dispatch: `POST /api/a2a/{ns}/{agent}` method `message/stream` (SSE).
Schema: [kagent-a2a-dispatch-evidence.md](../reference/kagent-a2a-dispatch-evidence.md).
Live L4 evidence: `evidence/kagent/educational-practice-phase-5d-trustworthy-a2a.md`.

### Agent-mediated MCP correlation helper

```powershell
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
python scripts/kagent/agent_mcp_trace.py --controller http://127.0.0.1:8083 --output json
```

Requires an observable `k8s_get_resources` invocation correlated to the A2A
taskId from the same Phase 5E dispatch (agent/tool/model structured part or
bounded correlated logs), normalized `pod`/`kagent` arguments, same-task names
returned after the observation, a repo-contained source record, and a
recomputed kubectl name match. The helper observes the actual kubectl context;
it must be `docker-desktop`. `FullMcpExecution` does not send a second A2A task.
Schema: [kagent-agent-mediated-mcp-evidence.md](../reference/kagent-agent-mediated-mcp-evidence.md).
Live attempt: `evidence/kagent/educational-practice-phase-5e-agent-mediated-mcp.md`
(L6 Not proven; L4 unchanged).

### Direct MCP session smoke

Learner-owned port-forward, then the session helper. A successful live run proves
**direct MCP tool invocation only**. It does **not** prove L6 agent-mediated
tool use. Live evidence: `evidence/kagent/educational-practice-phase-5b-direct-mcp.md`.

```powershell
kubectl port-forward -n kagent svc/kagent-tool-server 8000:8000
python scripts/kagent/mcp_session_smoke.py --url http://127.0.0.1:8000/mcp --output json --resource-type pod --resource-namespace kagent
```

Expected: exit code `0`, `sessionId` reported as `present` (never print the raw
value), `toolCallSucceeded: true`, and a `cleanup` status such as `deleted`.

If cleanup fails (e.g. DELETE returns a server error), the script exits 1 to
prevent silent session leaks. HTTP 405 (Method Not Allowed) on cleanup is benign
and does not cause a failure.

Problem context: `evidence/kagent/problems/2026-07-17-mcp-session-reuse.md`.

## Known Limitations

1. **Blocking A2A methods** `tasks/sendTask` and empty-param `message/send` /
   `message/stream` probes still return JSON-RPC errors on controller 0.9.11.
   Use the pinned MessageSendParams `message/stream` path documented above.
   Historical phase 5 failures remain in
   `evidence/kagent/educational-practice-phase-5.md`.

2. **`kagent-grafana-mcp` RemoteMCPServer `Accepted=False`** is the remaining
   expected degraded-lab state. The controller cannot reach the backing service at
   `http://kagent-grafana-mcp.kagent:8000/mcp` because no MCP server is deployed there.
   `kagent-tool-server` was in this state before Subphase 4C (July 16, 2026) and
   is now `Accepted=True` with a real MCP server deployed behind it via the
   `deploy/base/kagent/kagent-tool-server-runtime.yaml` manifest.

3. **Pod restart counts increase with each `helm upgrade`.** Each Helm upgrade
   triggers a rolling restart. On a fresh install most pods show 1 restart
   (the initial container start). After multiple upgrades, counts can grow:
   most pods accumulate restarts from each rollout, while the controller and
   UI pods accumulate additional restarts from the initial secret-not-found
   cycle. Restart counts do not affect pod readiness (`1/1 Running`) or agent
   acceptance.

4. **Port-forward sessions** block the terminal. Use separate terminals or
   `Start-Process` for background port-forwards.

5. **Terminal stream state may be `failed`** (for example model quota) after
   `submitted`/`working`. L4 is still proven when an accepted state with a
   non-empty task id was observed; that does not prove L6.

## Verdict Script (One-Command Lab Check)

Run this after applying manifests and port-forwards:

```powershell
# 1. Health check
.\scripts\kagent\check-kagent-health.ps1

# 2. A2A card fetch
python scripts/kagent/test-a2a-agent.py card

# 3. UI check
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:8080
```

If step 1 exits 0, step 2 prints `Accepted: True`, and step 3 prints `200`,
the lab is working.

## Related Docs

- [Deploy structure](../../deploy/README.md)
- [kagent educational roadmap](../onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
- [kagent current evidence and flaw ledger](../../evidence/kagent/README.md)
- [kagent capability definitions](../reference/kagent-capability-matrix.md)
- [documentation organization rules](../DOCUMENTATION-ORGANIZATION.md)
- [scripts/kagent/check-kagent-health.ps1](../../scripts/kagent/check-kagent-health.ps1)
- [scripts/kagent/KagentHealth.psm1](../../scripts/kagent/KagentHealth.psm1)
- [kagent health profiles](../reference/kagent-health-profiles.md)
- [kagent-a2a-dispatch-evidence.md](../reference/kagent-a2a-dispatch-evidence.md)
- [scripts/kagent/test-a2a-agent.py](../../scripts/kagent/test-a2a-agent.py)
- [scripts/kagent/mcp_session_smoke.py](../../scripts/kagent/mcp_session_smoke.py)
- [docs/onboarding/GETTING-STARTED.md](../onboarding/GETTING-STARTED.md)
