# kagent Educational Practice: Phase 4A Design

## Goal

Design the minimal MCP server deployment that will satisfy the existing
`RemoteMCPServer/kagent-tool-server` URL so it can reach `Accepted=True`.

## Server Selection

| Criterion | Choice |
|-----------|--------|
| Image | `ghcr.io/kagent-dev/kagent/tools:0.0.13` |
| Source | github.com/kagent-dev/tools (official) |
| Protocol | STREAMABLE_HTTP |
| Default MCP endpoint | `:8084/mcp` |
| In-cluster kubeconfig | Automatic (no extra mount needed) |
| Write safety | Kubernetes RBAC permits only `get`, `list`, and `watch`; image `0.0.13` does not support `--read-only` |
| Image verified | `docker pull` succeeded on 2026-07-16 |

Justification: the official kagent tools image is the exact MCP server the
RemoteMCPServer was designed to reference. It exposes the two tool names declared
in `deploy/samples/kagent/k8s-a2a-agent.yaml`:
- `k8s_get_resources`
- `k8s_get_available_api_resources`

## Tool Exposure

The server registers read and write tools, but its service account can perform
only `get`, `list`, and `watch` against the Kubernetes API. Write tools therefore
remain discoverable but fail authorization. A newer image with native
`--read-only` support would provide a cleaner tool surface.

## Transport and Service Mapping

The existing `deploy/base/kagent/kagent-tool-server.yaml` RemoteMCPServer defines:

```yaml
url: http://kagent-tool-server.kagent:8000/mcp
protocol: STREAMABLE_HTTP
```

The runtime deployment creates:

- **Service name**: `kagent-tool-server` (namespace `kagent`)
- **Service port**: 8000
- **Target port**: 8084 (container's MCP server port)
- **Path**: `/mcp`

This satisfies the RemoteMCPServer URL without editing the base resource.

## Service Name Decision: kagent-tool-server

The Service is intentionally named `kagent-tool-server` (matching the
RemoteMCPServer's `name` field). This makes DNS resolution work:

- RemoteMCPServer targets `http://kagent-tool-server.kagent:8000/mcp`
- Kubernetes DNS resolves `kagent-tool-server.kagent` to the Service
- The controller connects to port 8000, which forwards to container port 8084

## Safety Analysis

| Concern | Mitigation |
|---------|------------|
| Write operations | RBAC denies Kubernetes API write verbs; write tools may still be advertised by this image |
| Cluster access | RBAC limited to `get`, `list`, `watch` verbs on core API resources |
| No secrets | No secret mounts required; the server uses in-cluster kubeconfig |
| Lab boundary | Only runs on local Docker Desktop Kubernetes; no production exposure |
| Restart risk | Single replica, no persistent state |

## Unchanged Resources

- `deploy/base/kagent/kagent-tool-server.yaml` -- not modified
- `deploy/samples/kagent/k8s-a2a-agent.yaml` -- not modified
- `scripts/kagent/check-kagent-health.ps1` -- not modified (already handles both states)
- `scripts/kagent/test-a2a-agent.py` -- not modified (phase 3 changes are sufficient)

## Read-Only Limitation

The `0.0.13` Python tools server does not support the `--read-only` flag
(added in the v0.2.x Go implementation). The `--read-only` flag was omitted
from the manifest. The RBAC rules in the manifest provide the read-only
guarantee at the Kubernetes API level: only `get`, `list`, `watch` verbs are
granted. This is functionally equivalent for the lab -- the server process
may register write tools (like `k8s_delete_resource`) but those calls will
fail at the RBAC layer.

## Probe Note

The Go-based tools server (image:0.0.13) does not expose an HTTP `/health`
endpoint. The manifest uses TCP probes on port 8084 instead of HTTP probes.
This is sufficient for the educational lab.

## Next Step (Subphase 4B)

Create `deploy/base/kagent/kagent-tool-server-runtime.yaml` containing
ServiceAccount, ClusterRole (read-only), ClusterRoleBinding, Deployment,
and Service.
