# Implemented State and Roadmap

This document records the current observed state of the repository and the
local validation environment.

It answers four questions:

1. What is implemented now?
2. What can be used today?
3. What is only partially working?
4. What should be stabilized or refactored next?

## Current Implemented State

### Host-level MCP setup

Implemented and documented:

- VS Code user-level MCP registration
- Cursor user-level MCP registration
- Codex CLI MCP registration
- Continue MCP registration
- shared `playwright-global` naming and pinned Playwright MCP version

Primary artifacts:

- `scripts/install-global-playwright-mcp.ps1`
- `scripts/verify-global-playwright-mcp.ps1`
- `scripts/rollback-global-playwright-mcp.ps1`
- `scripts/McpConfigTargets.ps1`
- `config/templates/`

### Browser automation learning path

Implemented and documented:

- local Playwright exercises
- remote Docker browser scaffold
- SSH tunnel workflow
- troubleshooting guidance

Primary artifacts:

- `docs/02-LOCAL-PLAYWRIGHT-LAB.md`
- `docs/03-REMOTE-PLAYWRIGHT-LAB.md`
- `docs/TROUBLESHOOTING.md`
- `server/compose.yaml`
- `server/README.md`

### Agent-host documentation model

Implemented and documented:

- shared repo rules in `AGENTS.md`
- VS Code-specific repo instructions
- Continue slash-command personas
- explicit host-surface separation for Cursor, Continue, VS Code, and Codex

Primary artifacts:

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/instructions/`
- `.github/agents/`
- `.github/prompts/`
- `docs/ai-tooling.md`

### Tooling scaffold

Implemented and documented:

- Python toolchain scaffold
- Kubernetes validation scaffold
- security scan scaffold
- Azure and Foundry placeholder integration scaffold

Primary artifacts:

- `pyproject.toml`
- `.pre-commit-config.yaml`
- `.vscode/tasks.json`
- `scripts/quality/`
- `scripts/kubernetes/validate.ps1`
- `scripts/security/scan.ps1`
- `config/integrations/`

### Local kagent path

Implemented and partially validated:

- local `kagent` CRDs installed
- local `kagent` controller and UI running in `docker-desktop`
- local UI reachable on `http://localhost:8080` through port-forward
- starter A2A manifest committed in `deploy/base/kagent/k8s-a2a-agent.yaml`

Observed local state on 2026-07-09:

- `kagent-controller`: running
- `kagent-ui`: running
- `kagent-kmcp-controller-manager`: running
- `kagent-postgresql`: running
- `kagent-grafana-mcp`: running
- `kagent-querydoc`: running
- `promql-agent`: failing with `CreateContainerConfigError`
- `k8s-a2a-agent`: created but not accepted because `RemoteMCPServer "kagent-tool-server"` was not found

That means the local cluster path has moved past design-only documentation, but
the local A2A path is not yet fully ready.

## How To Use What Exists Today

### Fast path: host-level browser automation

Use this when you want the stable part of the repo:

```powershell
.\scripts\install-global-playwright-mcp.ps1
.\scripts\verify-global-playwright-mcp.ps1
codex mcp list
```

Then work through:

1. `docs/01-MCP-MENTAL-MODEL.md`
2. `docs/02-LOCAL-PLAYWRIGHT-LAB.md`
3. `docs/03-REMOTE-PLAYWRIGHT-LAB.md`

### Local kagent path

Use this when you want the current cluster-based learning path:

1. Read `docs/06-LOCAL-KAGENT-A2A-LAB.md`
2. Confirm the `docker-desktop` context
3. Confirm the `kagent` namespace workloads
4. Port-forward the UI service
5. Open `http://localhost:8080`
6. Inspect `kubectl get agent -n kagent`
7. Fix the known local issues before relying on A2A

Useful commands:

```powershell
kubectl config current-context
kubectl get pods -n kagent
kubectl get agent -n kagent
kubectl port-forward -n kagent svc/kagent-ui 8080:8080
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8080
```

### Review and validation path

Use this when you are changing configuration or docs:

```powershell
.\scripts\verify-global-playwright-mcp.ps1
pwsh -ExecutionPolicy Bypass -File scripts\kubernetes\validate.ps1
pwsh -ExecutionPolicy Bypass -File scripts\evaluation\run-evaluation.ps1
```

## Known Gaps

### Stable and repeatable

- global Playwright host registration
- local Playwright learning path
- remote browser Docker scaffold
- multi-host documentation and templates

### Working but still rough

- local `kagent` installation path
- local `kagent` UI validation
- starter A2A manifest committed to the repo

### Not yet closed

- `promql-agent` secret dependency not resolved
- `k8s-a2a-agent` references a missing `RemoteMCPServer`
- local `kagent` flow has not been reduced to a fully repeatable one-command setup
- `README.md` and some older docs still contain mojibake from earlier encoding damage
- the repo still uses historical plan docs as part of the main reading path even when current-state docs are more important

## Practical Roadmap

### Stage 1: Stabilize current behavior

1. Make the local `kagent` path reproducible without ad hoc recovery steps.
2. Resolve or disable default agents that block namespace health.
3. Fix the sample A2A manifest so it references existing cluster resources.
4. Normalize remaining encoding damage in top-level docs.

### Stage 2: Separate current state from history

1. Keep `README.md` short and current-state oriented.
2. Move historical strategy and archival planning into secondary docs.
3. Use one document for implemented state and one for target architecture.
4. Keep runbooks operational and time-aware.

### Stage 3: Make the repo easier to scale

1. Separate docs by purpose: onboarding, runbooks, architecture, reference, archive.
2. Separate deploy assets by runtime: local sample manifests, reusable base manifests, environment overlays, policies.
3. Keep validation scripts grouped by lifecycle step, not just by technology.
4. Add a thin operations layer for recurring health checks and recovery steps.

### Stage 4: Finish the cluster story

1. Provide a repeatable local `kagent` install flow.
2. Provide a validated A2A example that reaches `Accepted=True` and `Ready=True`.
3. Add a documented Playwright-to-`kagent` integration path only after the local A2A path is stable.

## Recommended Next Steps

If the goal is immediate usefulness:

1. keep using the Playwright host setup as the stable path
2. treat local `kagent` as the active lab
3. fix the `kagent` agent and secret issues before adding more cluster features

If the goal is repo scalability:

1. adopt the target structure in `docs/architecture/SCALABLE-REFACTOR-PLAN.md`
2. move toward purpose-based documentation
3. stop adding new behavior to the historical plan documents
