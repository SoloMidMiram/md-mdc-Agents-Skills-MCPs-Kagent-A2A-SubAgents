# Local kagent + A2A Lab

This runbook is the shortest path from a local Kubernetes cluster to a simple
`kagent` Agent-to-Agent (A2A) experiment.

## Current Local State

Observed on this machine on July 9, 2026:

- Docker is running.
- `kubectl` is targeting the `docker-desktop` context.
- `kagent` CRDs are installed.
- the `kagent` namespace exists and core workloads are running.
- the UI is reachable on `http://localhost:8080` through port-forward and has returned HTTP `200`.
- `promql-agent` is failing with `CreateContainerConfigError`.
- `k8s-a2a-agent` exists but is not accepted because `RemoteMCPServer "kagent-tool-server"` was not found.

That means the local cluster path is already installed and the current task is
stabilization, not initial discovery.

## Mental Model

Learn these pieces in order:

1. Kubernetes cluster
2. namespaces, pods, services, deployments
3. Helm
4. `kagent`
5. A2A agent status
6. A2A endpoint consumption

You do not need full Kubernetes depth before using `kagent`. You need enough
to inspect state, reconcile manifests, and debug dependencies.

## Phase 1: Learn Just Enough Kubernetes

Run these until the output feels familiar:

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get ns
kubectl get pods -A
kubectl get svc -A
kubectl describe node desktop-control-plane
```

Core ideas:

- `context`: which cluster `kubectl` talks to
- `namespace`: logical boundary in the cluster
- `pod`: running unit
- `service`: stable network address for pods
- `deployment`: controller that keeps pods running
- `port-forward`: temporary laptop-to-cluster tunnel

## Phase 2: Install Helm

If Helm is not installed on the machine, install it first and confirm:

```powershell
helm version
```

Use Helm for local Windows setup. It is the simplest repeatable path for
reconciling `kagent` resources.

## Phase 3: Install or Reconcile kagent

Create the namespace safely:

```powershell
kubectl create namespace kagent --dry-run=client -o yaml | kubectl apply -f -
```

Install or reconcile the CRDs:

```powershell
helm upgrade --install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds `
  --namespace kagent
```

Set the model provider key in the current shell:

```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```

Install or reconcile `kagent`:

```powershell
helm upgrade --install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent `
  --namespace kagent `
  --set providers.default=openAI `
  --set providers.openAI.apiKey=$env:OPENAI_API_KEY
```

Watch workloads:

```powershell
kubectl get pods -n kagent -w
```

## Phase 4: Open the kagent UI

Port-forward the UI service:

```powershell
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
```

Then open:

```text
http://localhost:8080
```

Windows `curl.exe` note:

- do not use `/dev/null` on Windows
- use `NUL` instead

```powershell
curl.exe -i http://localhost:8080
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8080
```

If the second command prints `200`, the UI is healthy even if an older
`/dev/null` command produced a false-positive exit code.

## Phase 5: Apply The Starter A2A Manifest

Starter manifest:

- [deploy/base/kagent/k8s-a2a-agent.yaml](/F:/Git/MCPtest/deploy/base/kagent/k8s-a2a-agent.yaml)

Apply and inspect:

```powershell
kubectl apply -f deploy/base/kagent/k8s-a2a-agent.yaml
kubectl get agent -n kagent
kubectl describe agent k8s-a2a-agent -n kagent
kubectl get remotemcpserver -n kagent
```

Current repo reality:

- the manifest creates `k8s-a2a-agent`
- the agent expects a `RemoteMCPServer` named `kagent-tool-server`
- the local cluster does not currently have that resource
- the agent therefore does not reach `Accepted=True`

## Phase 6: Verify The A2A Endpoint

Only do this after the agent reports as accepted and ready.

Port-forward the controller:

```powershell
kubectl port-forward svc/kagent-controller 8083:8083 -n kagent
```

Fetch the agent card:

```powershell
curl.exe http://localhost:8083/api/a2a/kagent/k8s-a2a-agent/.well-known/agent.json
```

If that returns JSON, A2A is working.

If it does not:

```powershell
kubectl get agent -n kagent
kubectl describe agent k8s-a2a-agent -n kagent
kubectl get remotemcpserver -n kagent
```

## Phase 7: Minimal A2A Experience

The smallest useful loop is:

1. create an agent with `a2aConfig.skills`
2. expose it through the controller on port `8083`
3. read the agent card from `.well-known/agent.json`
4. invoke the agent from a client

Good first prompts after the sample agent is healthy:

- `Get the pods in the kagent namespace`
- `Get all resources in the default namespace`

## Common Local Failure Points

- wrong context: confirm `kubectl config current-context` is `docker-desktop`
- pods not ready: inspect with `kubectl get pods -n kagent` and `kubectl describe pod <name> -n kagent`
- UI not reachable: check whether the `port-forward` shell is still running
- `promql-agent` failing: inspect secret dependencies in the `kagent` namespace
- `k8s-a2a-agent` not accepted: inspect `kubectl get remotemcpserver -n kagent` and fix the missing `kagent-tool-server` dependency
- no A2A card: verify the controller service exists and the agent is accepted before testing the endpoint

## Suggested Next Step

Before adding more agents or more integrations:

1. make the sample agent accepted and ready
2. resolve or intentionally disable broken default agents
3. document the final repeatable local install and validation path

## Related Docs

- [docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md](/F:/Git/MCPtest/docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md)
- [docs/04-KAGENT-INTEGRATION.md](/F:/Git/MCPtest/docs/04-KAGENT-INTEGRATION.md)
- [docs/architecture/SCALABLE-REFACTOR-PLAN.md](/F:/Git/MCPtest/docs/architecture/SCALABLE-REFACTOR-PLAN.md)
- [scripts/kubernetes/validate.ps1](/F:/Git/MCPtest/scripts/kubernetes/validate.ps1)
