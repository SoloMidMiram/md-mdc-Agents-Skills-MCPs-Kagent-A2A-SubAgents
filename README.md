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
.\scripts\install-global-playwright-mcp.ps1 -WhatIf      # preview changes
.\scripts\install-global-playwright-mcp.ps1               # apply
.\scripts\verify-global-playwright-mcp.ps1                # confirm
codex mcp list
```

Primary docs:

- [Getting started](docs/onboarding/GETTING-STARTED.md)
- [Educational projects map](docs/onboarding/EDUCATIONAL-PROJECTS.md)
- [Educational lanes architecture](docs/architecture/EDUCATIONAL-LANES-ARCHITECTURE.md)
- [Educational problem manual](docs/runbooks/educational-problem-manual.md)
- [kagent educational roadmap](docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
- [kagent evidence and current status](evidence/kagent/README.md)
- [documentation organization guide](docs/DOCUMENTATION-ORGANIZATION.md)
- [Implemented work narrative](docs/onboarding/IMPLEMENTED-WORK-NARRATIVE.md)
- [Implemented state and roadmap](docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md)
- [Portable settings bundle](docs/reference/portable-settings-bundle.md)
- [Glossary](docs/reference/GLOSSARY.md)
- [Project constraints](constraints.md)
- [Scalable refactor plan](docs/architecture/SCALABLE-REFACTOR-PLAN.md)

Runbooks:

- [Local Playwright lab](docs/runbooks/local-playwright-lab.md)
- [Remote Playwright lab](docs/runbooks/remote-playwright-lab.md)
- [Local kagent A2A lab](docs/runbooks/local-kagent-a2a-lab.md)
- [SSH concurrency fix](docs/runbooks/ssh-concurrency-fix.md)
- [Troubleshooting](docs/runbooks/troubleshooting.md)

## Current State

Two paths matter today:

- **Stable path**: user-level `playwright-global` registration across VS Code, Cursor, Codex, and Continue. Verified by repeatable install (`-WhatIf` first) / verify / rollback / verify round-trip, covered by 73+ Pester tests, and covered by CI configuration on push and pull_request.
  `laptop-stable-v0.1` is tagged at `cdb7dc0`; this tree targets patch `laptop-stable-v0.1.1` (UTF-8 onboarding, narrative sync, bridge manifests).
- **Active lab path**: local `kagent` on `docker-desktop` uses the controller's
  native `/mcp` surface (`list_agents` and `invoke_agent`). L4/L5 are Proven;
  I0-I2 are Proven; I3 is Blocked (provider region policy; no Cursor I3 gate yet);
  L6/L7 remain Not
  proven. See the [canonical evidence index](evidence/kagent/README.md) for
  dated status and capability decisions.

Use [docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md](docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md)
for the learning path, [docs/runbooks/local-kagent-a2a-lab.md](docs/runbooks/local-kagent-a2a-lab.md)
for the cluster runbook, and [docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md](docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md)
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
| Local Kubernetes and `kagent` | `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`, `docs/runbooks/local-kagent-a2a-lab.md`, `deploy/base/kagent/`, `deploy/samples/kagent/` | Native controller `/mcp` federation: I0-I2 Proven; I3 Blocked |

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
| `scripts/kagent/controller_mcp_smoke.py` | Verify the bounded native controller MCP contract |

## kagent Roadmap

The stable Playwright release lane remains separately tracked in
[the implemented state and roadmap](docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md).
The detailed kagent learning path lives in the
[kagent educational roadmap](docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md).

Current kagent priority order:

1. **Native delegation** — complete Phase 6 federation through the controller's
   `/mcp` surface, without a custom A2A bridge.
2. **Read-only I4/L6 evidence** — remove mutation-capable tools from discovery
   and capture one same-invocation Kubernetes result with a `kubectl` match.
3. **Repeatability** — automate a clean-install workshop with restart, cleanup,
   I5, and L7 evidence.

## Repository Map

```text
.
|-- constraints.md              Non-negotiables and project invariants
|-- REPO_MANIFEST.yaml          Flat index of repo artifacts (machine-readable)
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
|   `-- 01-*.md–07-*.md          Root-level compat redirects only
|-- evidence/                   Validation evidence
|-- scripts/
|   |-- kagent/                  kagent health checks and A2A helpers
|   `-- ...                      Install, verify, evaluation, quality, k8s
`-- server/                     Remote Playwright Docker runtime
```

## Reading Order

1. `docs/onboarding/GETTING-STARTED.md`
2. `docs/onboarding/KAGENT-EDUCATIONAL-ROADMAP.md`
3. `docs/onboarding/IMPLEMENTED-STATE-AND-ROADMAP.md`
4. `docs/01-MCP-MENTAL-MODEL.md`
5. `docs/reference/portable-settings-bundle.md`
6. `docs/runbooks/local-playwright-lab.md`
7. `docs/runbooks/remote-playwright-lab.md`
8. `docs/runbooks/local-kagent-a2a-lab.md`
9. `docs/architecture/SCALABLE-REFACTOR-PLAN.md`
10. `docs/integrations/AI-TOOLING-INTEGRATION-PLAN.md`
11. `docs/04-KAGENT-INTEGRATION.md`
12. `docs/runbooks/troubleshooting.md`

## Key Concepts

- MCP is not built into the editor. The editor is the host and the MCP server is a separate process.
- There is no shared cross-IDE MCP registry. Each host reads its own config format from its own location.
- "Global" in this repo means user-level registration in every supported host, not one system-wide toggle.

## License

MIT - see [LICENSE](LICENSE).

*Last updated: 2026-07-31*
