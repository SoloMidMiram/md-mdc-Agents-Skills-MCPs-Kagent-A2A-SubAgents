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

- [Getting started](docs/GETTING-STARTED.md)
- [Portable settings bundle](docs/PORTABLE-SETTINGS-BUNDLE.md)
- [Implemented state and roadmap](docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md)
- [Scalable refactor plan](docs/architecture/SCALABLE-REFACTOR-PLAN.md)

## Current State

Two paths matter today:

- Stable path: user-level Playwright MCP registration across VS Code, Cursor, Codex, and Continue
- Active lab path: local `kagent` and A2A setup on `docker-desktop`, with the UI working and the sample agent still needing stabilization

Current local `kagent` observations from July 9, 2026:

- core `kagent` workloads are running in the `kagent` namespace
- the UI serves HTTP `200` on `http://localhost:8080` through port-forward
- `promql-agent` is failing with `CreateContainerConfigError`
- `k8s-a2a-agent` is not accepted because `RemoteMCPServer "kagent-tool-server"` is missing

Use [docs/06-LOCAL-KAGENT-A2A-LAB.md](docs/06-LOCAL-KAGENT-A2A-LAB.md) for the
cluster runbook and [docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md](docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md)
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
| Browser automation | `docs/02-LOCAL-PLAYWRIGHT-LAB.md`, `docs/03-REMOTE-PLAYWRIGHT-LAB.md`, `server/` | Stable |
| Host configuration portability | `config/templates/`, `docs/PORTABLE-SETTINGS-BUNDLE.md` | Stable |
| AI tooling scaffold | `.vscode/settings.json`, `config/integrations/`, `docs/ai-tooling.md` | Implemented |
| Local Kubernetes and `kagent` | `docs/06-LOCAL-KAGENT-A2A-LAB.md`, `deploy/base/kagent/` | Installed but still rough |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/install-global-playwright-mcp.ps1` | Register Playwright in all supported hosts |
| `scripts/verify-global-playwright-mcp.ps1` | Validate host registrations |
| `scripts/rollback-global-playwright-mcp.ps1` | Restore backed-up host config |
| `scripts/bootstrap-python-workspace.ps1` | Bootstrap the local Python toolchain |
| `scripts/evaluation/run-evaluation.ps1` | Run the Pester evaluation suite |
| `scripts/kubernetes/validate.ps1` | Validate Kubernetes-related repo assets |

## Roadmap

Near-term priorities:

1. Make the local `kagent` install and recovery flow repeatable.
2. Fix the sample A2A path so `k8s-a2a-agent` reaches `Accepted=True`.
3. Keep top-level docs focused on current behavior instead of historical plan state.
4. Move the repo toward purpose-based documentation and runtime-based deploy assets.

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
|   `-- base/kagent/            Starter local kagent manifests
|-- docs/
|   |-- GETTING-STARTED.md
|   |-- PORTABLE-SETTINGS-BUNDLE.md
|   |-- 01-MCP-MENTAL-MODEL.md
|   |-- 02-LOCAL-PLAYWRIGHT-LAB.md
|   |-- 03-REMOTE-PLAYWRIGHT-LAB.md
|   |-- 04-KAGENT-INTEGRATION.md
|   |-- 05-SSH-CONCURRENCY-FIX.md
|   |-- 06-LOCAL-KAGENT-A2A-LAB.md
|   |-- 07-IMPLEMENTED-STATE-AND-ROADMAP.md
|   |-- ai-tooling.md
|   |-- architecture/
|   `-- integrations/
|-- evidence/                   Validation evidence
|-- scripts/                    Install, verify, evaluation, quality, and k8s scripts
`-- server/                     Remote Playwright Docker runtime
```

## Reading Order

1. `docs/GETTING-STARTED.md`
2. `docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md`
3. `docs/01-MCP-MENTAL-MODEL.md`
4. `docs/PORTABLE-SETTINGS-BUNDLE.md`
5. `docs/02-LOCAL-PLAYWRIGHT-LAB.md`
6. `docs/03-REMOTE-PLAYWRIGHT-LAB.md`
7. `docs/06-LOCAL-KAGENT-A2A-LAB.md`
8. `docs/architecture/SCALABLE-REFACTOR-PLAN.md`
9. `docs/integrations/AI-TOOLING-INTEGRATION-PLAN.md`
10. `docs/04-KAGENT-INTEGRATION.md`
11. `docs/TROUBLESHOOTING.md`

## Key Concepts

- MCP is not built into the editor. The editor is the host and the MCP server is a separate process.
- There is no shared cross-IDE MCP registry. Each host reads its own config format from its own location.
- "Global" in this repo means user-level registration in every supported host, not one system-wide toggle.
- The local `kagent` path is real now, but it is still a lab and not yet a clean baseline.

## License

MIT - see [LICENSE](LICENSE).

*Last updated: 2026-07-09*
