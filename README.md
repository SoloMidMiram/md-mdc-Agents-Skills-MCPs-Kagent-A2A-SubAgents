# MCP Agent Tooling Laboratory

[![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-2563EB)](#)
[![Playwright](https://img.shields.io/badge/Playwright-MCP_Server-45BA4B)](https://github.com/microsoft/playwright-mcp)
[![VS Code](https://img.shields.io/badge/VS_Code-Agent_MCP-007ACC)](#)
[![Cursor](https://img.shields.io/badge/Cursor-Agent_MCP-6C47FF)](#)
[![Codex CLI](https://img.shields.io/badge/Codex_CLI-Agent_MCP-000000)](#)
[![Continue](https://img.shields.io/badge/Continue-Agent_MCP-FF6B35)](#)
[![CI](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/workflows/quality.yml/badge.svg)](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/workflows/quality.yml)

Portable MCP host setup, browser automation labs, and a local `kagent` A2A lab
for VS Code, Cursor, Codex CLI, and Continue.

## Quick Start

```powershell
git clone https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents.git
cd md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents
.\scripts\install-global-playwright-mcp.ps1
.\scripts\verify-global-playwright-mcp.ps1
codex mcp list
```

Primary docs:

- [Getting started](docs/onboarding/GETTING-STARTED.md)
- [Implemented state and roadmap](docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md)
- [Portable settings bundle](docs/reference/portable-settings-bundle.md)
- [Scalable refactor plan](docs/architecture/SCALABLE-REFACTOR-PLAN.md)

Runbooks:

- [Local Playwright lab](docs/runbooks/local-playwright-lab.md)
- [Remote Playwright lab](docs/runbooks/remote-playwright-lab.md)
- [Local kagent A2A lab](docs/runbooks/local-kagent-a2a-lab.md)
- [SSH concurrency fix](docs/runbooks/ssh-concurrency-fix.md)
- [Troubleshooting](docs/runbooks/troubleshooting.md)

## Current State

Two paths matter today:

- Stable path: user-level Playwright MCP registration across VS Code, Cursor, Codex, and Continue
- Active lab path: local `kagent` and A2A setup on `docker-desktop`, with all agents accepted and ready

Current local `kagent` observations from July 9, 2026:

- all 17 core `kagent` workloads are `1/1 Running` in the `kagent` namespace
- the UI serves HTTP `200` on `http://localhost:8080` through port-forward
- `k8s-a2a-agent`: **Accepted=True, Ready=True** (RemoteMCPServer `kagent-tool-server` created)
- all agents including `promql-agent`: **Running and Accepted=True** (secrets resolved)
- A2A agent card accessible via `kagent-controller` REST API on port 8083
- A2A JSON-RPC `tasks/sendTask` not exposed in current controller version (use `a2a-cli`)

Use [docs/runbooks/local-kagent-a2a-lab.md](docs/runbooks/local-kagent-a2a-lab.md) for the
cluster runbook and [docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md](docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md)
for the current repo-wide status.

## What's Inside

### Host configuration

| Host | What it gets | Config location |
|------|--------------|-----------------|
| VS Code Copilot | 7 MCP servers and repo instructions | `%APPDATA%\Code\User\mcp.json` |
| Cursor Agent | Playwright MCP and repo contract | `%USERPROFILE%\.cursor\mcp.json` |
| Codex CLI | Playwright MCP and sandbox config | `%USERPROFILE%\.codex\config.toml` |
| Continue | Models, slash-command personas, Playwright MCP, rules | `%USERPROFILE%\.continue\config.yaml` |

### Main runtime areas

| Area | Primary artifacts | Status |
|------|-------------------|--------|
| Browser automation | `docs/runbooks/local-playwright-lab.md`, `docs/runbooks/remote-playwright-lab.md`, `server/` | Stable |
| Host configuration portability | `config/templates/`, `docs/reference/portable-settings-bundle.md` | Stable |
| AI tooling scaffold | `.vscode/settings.json`, `config/integrations/`, `docs/ai-tooling.md` | Implemented |
| Local Kubernetes and `kagent` | `docs/runbooks/local-kagent-a2a-lab.md`, `deploy/base/kagent/`, `deploy/samples/kagent/` | A2A sample agent accepted and ready |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/install-global-playwright-mcp.ps1` | Register Playwright in all supported hosts |
| `scripts/verify-global-playwright-mcp.ps1` | Validate host registrations |
| `scripts/rollback-global-playwright-mcp.ps1` | Restore backed-up host config |
| `scripts/bootstrap-python-workspace.ps1` | Bootstrap the local Python toolchain |
| `scripts/evaluation/run-evaluation.ps1` | Run the Pester evaluation suite |
| `scripts/kubernetes/validate.ps1` | Validate Kubernetes-related repo assets |
| `scripts/kagent/check-kagent-health.ps1` | Inspect kagent pod/agent/RemoteMCPServer health |
| `scripts/kagent/test-a2a-agent.py` | Fetch A2A agent card and test A2A dispatch |

## Roadmap

Next-stage priorities:

1. **A2A task dispatch via `a2a-cli`** — the controller exposes agent card discovery via REST on port 8083. The next step is to use `a2a-cli` (or a compatible client) for JSON-RPC `tasks/sendTask` delivery.
2. **Optional real MCP server for `kagent-tool-server`** — `RemoteMCPServer/Accepted=False` is the expected degraded-lab state today. Deploying a lightweight MCP server behind the `kagent-tool-server` service makes the full tool-execution path testable.
3. **Finish doc stub cleanup** — root-level `docs/0x-*.md` files are now compat redirects only. A future pass can remove them after consumers have updated their bookmarks.

Architecture direction:

- onboarding docs should explain what works now
- runbooks should describe operational steps and failure recovery
- architecture docs should explain the target structure and runtime separation
- old plan-heavy documents should become secondary reference, not the default path

See [docs/architecture/SCALABLE-REFACTOR-PLAN.md](docs/architecture/SCALABLE-REFACTOR-PLAN.md)
for the target repo shape.

## Repository Map

```text
.
|-- .devcontainer/              Reproducible Linux development container
|-- .github/                    CI, prompts, agents, repo-specific instructions
|-- .project-ai/                Durable project memory and templates
|-- .vscode/                    Workspace settings, tasks, extensions
|-- config/                     Host templates and integration placeholders
|-- deploy/
|   |-- README.md                Deploy structure guide
|   |-- base/kagent/             Reusable shared resources (RemoteMCPServer)
|   `-- samples/kagent/          Sample A2A agent manifests
|-- docs/
|   |-- onboarding/              Getting started and implemented state
|   |-- runbooks/                Operational labs and troubleshooting
|   |-- reference/               Settings bundles and capability matrixes
|   |-- architecture/            Target structure and runtime separation plans
|   |-- integrations/            Host capability matrix and AI tooling plans
|   |-- archive/                 Historical plan documents (redirect source)
|   `-- 0x-*.md                  Root-level compat redirects only
|-- evidence/                   Validation evidence
|-- scripts/
|   |-- kagent/                  kagent health checks and A2A helpers
|   `-- ...                      Install, verify, evaluation, quality, k8s
`-- server/                     Remote Playwright Docker runtime
```

## Reading Order

1. `docs/onboarding/GETTING-STARTED.md`
2. `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`
3. `docs/01-MCP-MENTAL-MODEL.md`
4. `docs/reference/portable-settings-bundle.md`
5. `docs/runbooks/local-playwright-lab.md`
6. `docs/runbooks/remote-playwright-lab.md`
7. `docs/runbooks/local-kagent-a2a-lab.md`
8. `docs/architecture/SCALABLE-REFACTOR-PLAN.md`
9. `docs/integrations/AI-TOOLING-INTEGRATION-PLAN.md`
10. `docs/04-KAGENT-INTEGRATION.md`
11. `docs/runbooks/troubleshooting.md`

## Key Concepts

- MCP is not built into the editor. The editor is the host and the MCP server is a separate process.
- There is no shared cross-IDE MCP registry. Each host reads its own config format from its own location.
- "Global" in this repo means user-level registration in every supported host, not one system-wide toggle.
- The local `kagent` path is working: all 17 pods running, all agents Accepted=True, A2A agent card accessible via REST API.

## License

MIT - see [LICENSE](LICENSE).

*Last updated: 2026-07-09*
