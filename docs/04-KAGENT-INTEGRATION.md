# kagent Integration Design (Future)

This document describes how Playwright MCP can be integrated with **kagent** in a Kubernetes environment. Do not attempt this until local and Docker server deployments are fully validated.

---

## Prerequisites (not installed here)

- Kubernetes cluster (local: kind/minikube, or remote)
- Helm (package manager for Kubernetes)
- kubectl (Kubernetes CLI)
- kagent installed in the cluster
- Successful local and remote Docker Playwright MCP validation

---

## Architecture Options

### Architecture A: External Server MCP

```
kagent (in Kubernetes)
        │
        │ remote protected HTTP endpoint
        ▼
Playwright MCP (on your Linux server, not in Kubernetes)
        │
        ▼
Headless Chromium
```

**Pros:**
- Playwright runs on a separate machine, isolated from cluster workloads
- Easier to update/manage independently
- No container sandbox complexity in-cluster

**Cons:**
- Requires network connectivity and authentication between cluster and server
- Higher latency
- Additional security considerations for cross-cluster traffic

### Architecture B: Kubernetes-Native Service

```
kagent
        │
        │ ClusterIP Service
        ▼
Service: playwright-mcp.kagent.svc.cluster.local:8931
        │
        ▼
Pod: Playwright MCP container
        │
        ▼
Headless Chromium (same pod)
```

**Pros:**
- Everything inside Kubernetes, simpler network topology
- Managed via standard Kubernetes resources
- Lower latency between agent and browser

**Cons:**
- Chromium in container requires --no-sandbox
- Resource consumption in the cluster
- Browser state needs careful management

---

## Conceptual Future Commands

### Register Playwright MCP with kagent

```bash
# Architecture A: Remote endpoint
kagent add-mcp playwright \
    --remote http://playwright-mcp-server:8931/mcp

# Architecture B: Kubernetes service
kagent add-mcp playwright \
    --remote http://playwright-mcp:8931/mcp
```

### Using a RemoteMCPServer Resource (Architecture B)

```yaml
apiVersion: kagent.dev/v1alpha1
kind: RemoteMCPServer
metadata:
  name: playwright-mcp
  namespace: kagent
spec:
  transport: STREAMABLE_HTTP
  url: http://playwright-mcp:8931/mcp
```

---

## Playwright Verification Agent Design

Define a dedicated agent whose permissions are limited to browser-based verification:

```yaml
# Conceptual agent definition
name: deployment-verifier
model: gpt-4
tools:
  - kubernetes:       # Pod health, deployment status, logs
      operations: [read]
  - playwright-mcp:   # Browser automation
      operations: [navigate, read, screenshot-report]
      restrictions:
        allowed_origins:
          - "https://your-app.example.com"
          - "http://staging.internal"
        block_forms: true
        block_file_access: true
        block_destructive_navigation: true
```

### What This Agent Can Do
1. Open approved application URLs
2. Inspect page structure (headings, links, accessibility)
3. Check browser console for errors and warnings
4. List network requests and verify status codes
5. Navigate non-destructively between approved pages
6. Report results separately from conclusions

### What This Agent Must NOT Do
- Manage Kubernetes resources through Playwright (no kubectl via browser)
- Submit production forms, make purchases, or change account settings
- Upload secrets, credentials, or private data
- Expose the MCP endpoint publicly
- Navigate to unapproved origins or external domains

---

## Complementary Tools

Kubernetes-native tools and Playwright serve different roles:

| Tool | What it checks | Limitation |
|------|----------------|------------|
| `kubectl get pods` | Pod is running | Does not verify app is usable |
| `kubectl logs` | Log output | Does not verify UI behavior |
| `helm test` | Deployment health | Does not verify browser rendering |
| Prometheus | Metrics and alerts | Cannot measure user experience |
| **Playwright MCP** | Actual browser behavior | Cannot check infrastructure state |

**Powerful combination:**
> Kubernetes says: "The pod is alive."
> Playwright says: "The product is actually usable."

---

## Security Considerations

- Playwright MCP is not a security boundary — do not expose publicly
- Use Kubernetes NetworkPolicies to restrict access to the MCP pod
- Use `--allowed-origins` and `--blocked-origins` as guardrails (not as complete security)
- Never mount the Docker socket or host filesystem
- Run with `--isolated` to prevent state leaking between sessions
- Consider adding authentication middleware in front of the MCP endpoint

---

## Future Learning Path

1. Learn Kubernetes vocabulary (pods, deployments, services, namespaces)
2. Set up a local Kubernetes cluster (kind or minikube)
3. Install kagent via Helm
4. Deploy Playwright MCP as a Kubernetes Deployment
5. Connect kagent to Playwright MCP via ClusterIP Service
6. Build the verification agent with restricted permissions

*Do not skip local and Docker validation. Kubernetes adds five new concepts on top of MCP.*
