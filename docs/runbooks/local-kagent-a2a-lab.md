# Local kagent + A2A Lab

This runbook is the shortest path from a local Kubernetes cluster to a working
kagent A2A lab: deploy, reconcile, verify, and inspect the sample A2A agent.

## Lab Status Summary

As of July 9, 2026 the local kagent lab is in the following state:

- **Infrastructure:** 17/17 pods Running and Ready; 11/11 agents Accepted=True Ready=True.
- **REST agent card:** Reachable and returns full agent metadata (works).
- **JSON-RPC `tasks/sendTask`:** Not exposed by this controller version (returns `-32601`).
- **RemoteMCPServer:** Both `kagent-tool-server` and `kagent-grafana-mcp` exist with `Accepted=False` -- expected because no MCP server is deployed at their target URLs.
- **UI:** Reachable at `http://localhost:8080` (returns HTTP 200).
- **Controller API:** Reachable at `http://localhost:8083`.

## Current Local State

Observed on this machine on July 9, 2026:

- Docker Desktop cluster (context: `docker-desktop`).
- All 17 kagent pods are `Running` and `1/1 Ready`.
- All agents including `k8s-a2a-agent` show `Accepted=True` and `Ready=True`.
- `kagent-tool-server` RemoteMCPServer exists (agents depend on it).
- `kagent-grafana-mcp` and `kagent-tool-server` RemoteMCPServers show `Accepted=False`
  because no actual MCP server is deployed at their URLs -- this is expected in a lab.
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
$env:OPENAI_API_KEY = "your-api-key-here"
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

All pods should reach `1/1 Running`.

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

The lab uses two resources:

1. **`kagent-tool-server`** (`RemoteMCPServer`) - base resource shared by multiple agents
2. **`k8s-a2a-agent`** (`Agent`) - sample A2A agent for read-only cluster inspection

Apply the base resource first, then the sample agent:

```powershell
kubectl apply -f deploy/base/kagent/kagent-tool-server.yaml
kubectl apply -f deploy/samples/kagent/k8s-a2a-agent.yaml
```

Resources are organized as:

```
deploy/
  base/kagent/
    kagent-tool-server.yaml      # shared MCP server reference (reusable)
  samples/kagent/
    k8s-a2a-agent.yaml           # sample A2A agent (educational / lab use)
```

## Verify Health

### Quick health check

```powershell
.\scripts\kagent\check-kagent-health.ps1
```

This inspects:
- pod readiness (all pods 1/1 Running)
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

### A2A task dispatch via a2a-cli

The kagent controller's A2A endpoint at `/.well-known/agent.json` uses the A2A
protocol. The current controller version does not expose the `tasks/sendTask`
JSON-RPC method. For full A2A task dispatch, install and use the A2A CLI:

```powershell
pip install a2a-sdk
kubectl port-forward -n kagent svc/kagent-controller 8083:8083
a2a-cli --agent http://localhost:8083/api/a2a/kagent/k8s-a2a-agent
```

The REST API agent card fetch works reliably and verifies that the agent is
accepted, ready, and configured with the correct skills.

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

This exits non-zero on any failure and lists all detected issues.

## Known Limitations

1. **A2A task dispatch** via JSON-RPC `tasks/sendTask` is not available in the
   current kagent controller version. The agent card is fully accessible via the
   REST API at `/api/agents/{namespace}/{agent}`. Use `a2a-cli` for task dispatch.

2. **`kagent-tool-server` RemoteMCPServer `Accepted=False`** is an expected
   degraded-lab state. Agents require only that the `RemoteMCPServer` resource
   *exists*; the controller cannot reach the backing service at
   `http://kagent-tool-server.kagent:8000/mcp` because no MCP server is deployed
   there. This is acceptable for card and acceptance testing, and not acceptable
   for real tool execution.

3. **`kagent-grafana-mcp`** RemoteMCPServer is similarly `Accepted=False` for the
   same reason -- no backing service at its URL.

4. **All pods show 1 restart** on initial deploy (typical for Helm-managed
   rollouts). The kagent-controller and kagent-ui show 3-6 restarts from the
   initial secret-not-found cycle.

5. **Port-forward sessions** block the terminal. Use separate terminals or
   `Start-Process` for background port-forwards.

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
- [scripts/kagent/check-kagent-health.ps1](../../scripts/kagent/check-kagent-health.ps1)
- [scripts/kagent/test-a2a-agent.py](../../scripts/kagent/test-a2a-agent.py)
- [docs/onboarding/GETTING-STARTED.md](../onboarding/GETTING-STARTED.md)
