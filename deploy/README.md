# Deploy Structure

This directory organizes Kubernetes manifests for the kagent/A2A lab.

```
deploy/
  base/           Reusable shared resources (RemoteMCPServer, model configs, secrets)
    kagent/
      kagent-tool-server.yaml   # Kubernetes tool MCP server reference
  samples/        Educational / starter manifests for local lab use
    kagent/
      k8s-a2a-agent.yaml        # Sample A2A agent for read-only cluster inspection
```

Keep base resources generic and reusable. Add local-lab customizations as samples.
Do not treat sample manifests as production base assets.
