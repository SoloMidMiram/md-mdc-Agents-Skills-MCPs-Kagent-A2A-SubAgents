# Introduction to the MCPtest Laboratory

## What This Repo Is

This repository is a portable MCP learning and implementation lab. It combines:

- host-level MCP setup for VS Code, Cursor, Codex CLI, and Continue
- Playwright browser automation labs
- Docker-based remote browser runtime docs
- a local Kubernetes and `kagent` A2A lab

## What Works Today

| Capability | Status |
|-----------|--------|
| Playwright MCP host registration | Working and documented |
| Local browser automation exercises | Working and documented |
| Remote browser Docker scaffold | Implemented; needs a Linux server to use remotely |
| AI tooling scaffold and host guidance | Implemented |
| Local `kagent` namespace and UI | Installed and partially validated |
| Starter A2A manifest | Committed, but not yet stabilized |

## Current Local kagent Reality

The repo is past design-only kagent documentation.

Observed on this machine on July 9, 2026:

- the `kagent` namespace exists in the local `docker-desktop` cluster
- core `kagent` workloads are running
- the UI is reachable on `http://localhost:8080`
- `promql-agent` is failing because of a container configuration problem
- `k8s-a2a-agent` is not accepted because `RemoteMCPServer "kagent-tool-server"` is missing

Use these documents in order for cluster work:

1. `docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md`
2. `docs/06-LOCAL-KAGENT-A2A-LAB.md`
3. `docs/04-KAGENT-INTEGRATION.md`

## Quick Start

```powershell
git clone https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents.git
cd md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents
.\scripts\install-global-playwright-mcp.ps1
.\scripts\verify-global-playwright-mcp.ps1
codex mcp list
```

Then use:

- `docs/PORTABLE-SETTINGS-BUNDLE.md` for the full machine setup path
- `docs/02-LOCAL-PLAYWRIGHT-LAB.md` for safe browser exercises
- `docs/06-LOCAL-KAGENT-A2A-LAB.md` for the active local cluster lab

## Reading Order

1. `docs/07-IMPLEMENTED-STATE-AND-ROADMAP.md`
2. `docs/01-MCP-MENTAL-MODEL.md`
3. `docs/PORTABLE-SETTINGS-BUNDLE.md`
4. `docs/02-LOCAL-PLAYWRIGHT-LAB.md`
5. `docs/03-REMOTE-PLAYWRIGHT-LAB.md`
6. `docs/06-LOCAL-KAGENT-A2A-LAB.md`
7. `docs/architecture/SCALABLE-REFACTOR-PLAN.md`
8. `docs/integrations/`
9. `docs/04-KAGENT-INTEGRATION.md`
10. `docs/TROUBLESHOOTING.md`

## Key Concepts

### MCP Is Not Inside The Editor

The editor is the MCP host. The MCP server is a separate process or endpoint.
That separation explains most configuration and networking behavior in this
repo.

### Each Host Owns Its Own Config

| Host | Config path | Format |
|------|-------------|--------|
| VS Code | `%APPDATA%\Code\User\mcp.json` | JSON |
| Cursor | `%USERPROFILE%\.cursor\mcp.json` | JSON |
| Codex | `%USERPROFILE%\.codex\config.toml` | TOML |
| Continue | `%USERPROFILE%\.continue\config.yaml` | YAML |

### "Global" Means Per-Host User-Level Registration

This repo uses "global" to mean the MCP server is registered in each supported
host at the user level. It does not mean Windows or Docker provides one shared
registry for all tools.

## Directory Map

```text
F:\Git\MCPtest\
|-- .github\         CI, prompts, agents, repo instructions
|-- .project-ai\     Durable memory and templates
|-- .vscode\         Workspace settings and tasks
|-- config\          Host templates and integration placeholders
|-- deploy\          Local cluster manifests
|-- docs\            Onboarding, runbooks, architecture, and reference docs
|-- evidence\        Validation evidence
|-- scripts\         Install, verify, quality, and k8s scripts
`-- server\          Remote Playwright Docker runtime
```

> **Last updated:** 2026-07-09
> **Source repo:** `F:\Git\MCPtest`
