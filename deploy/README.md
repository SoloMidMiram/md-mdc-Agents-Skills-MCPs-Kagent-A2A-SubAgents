# Deploy Structure

This directory organizes Kubernetes manifests for the kagent/A2A lab.

```
deploy/
  base/           Reusable shared resources (RemoteMCPServer, model configs, secrets)
    kagent/
      kagent-tool-server.yaml           # Kubernetes tool MCP server reference (RemoteMCPServer CR)
      kagent-tool-server-runtime.yaml   # MCP server runtime (ServiceAccount, RBAC, Deployment, Service)
  samples/        Educational / starter manifests for local lab use
    kagent/
      k8s-a2a-agent.yaml        # Sample A2A agent for read-only cluster inspection
    kagent-a2a/                 # E1–E5 role manifests (Lane A; E1–E2 in PR #4)
      README.md                 # Index and example mapping
      01-planner/               # E1 — planner-only A2A
      02-reviewer/              # Phase 2 — reviewer agent
      03-supervisor/            # E2 — supervisor delegation
      04-docs-agent/            # E3 — docs validator
      05-telegram-capstone/     # E5 — full capstone workflow
```

Keep base resources generic and reusable. Add local-lab customizations as samples.
Do not treat sample manifests as production base assets.

`deploy/samples/kagent-a2a/` holds educational role manifests for the E1–E5
sequence. See `docs/north-star.md`, `docs/runbooks/kagent-a2a-examples.md`, and
`deploy/samples/kagent-a2a/README.md` for direction and procedures. E1–E2
manifests ship in PR #4 (`edu/kagent-a2a-role-examples`).
