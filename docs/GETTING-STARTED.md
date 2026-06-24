# Introduction to the MCPtest Laboratory

## What Is This?

A **MCP (Model Context Protocol) learning laboratory** and **portable developer
tooling environment**. It documents how to set up, validate, and integrate AI
agent tooling across VS Code, Cursor, Codex CLI, and the Continue extension —
all from one Git repository that you can clone onto any machine.

## Who Is This For?

- Developers who want **browser automation** available in their AI coding agents
- Teams adopting MCP across multiple editors (VS Code, Cursor, Codex)
- Anyone setting up a new development machine who needs to reproduce their
  agent/MCP environment quickly
- Students of the **kagent** and **Agent-to-Agent (A2A)** ecosystem

## What Can You Do?

### Already Working

| Capability | How |
|-----------|-----|
| **Browser automation from any agent** | `playwright-global` MCP server registered in VS Code, Cursor, Codex, and Continue |
| **Remote browser via Docker** | `server/compose.yaml` deploys Playwright MCP headless on Linux |
| **SSH tunnel** | Encrypted tunnel from local agents to remote browser |
| **Azure tooling (dormant)** | Azure MCP installed but stopped; read-only policy pre-configured |
| **Foundry Toolkit (local)** | Installed; no model run or cloud deployment yet |
| **Safe browser testing** | 10 exercises for navigation, accessibility, console, network |

### Planned / Future

| Capability | Status |
|-----------|--------|
| Kubernetes / kagent integration | Design complete (`docs/04-KAGENT-INTEGRATION.md`) |
| Remote HTTP MCP deployment | Docker ready; needs Linux server |
| Cursor Azure MCP bridge | Placeholder documented (`config/integrations/`) |
| Foundry cloud deployment | Placeholder documented (`config/integrations/`) |

## Quick Start (New Laptop)

```powershell
# 1. Clone
git clone https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents.git
cd md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents

# 2. Install Playwright MCP across all hosts
.\scripts\install-global-playwright-mcp.ps1

# 3. Verify
.\scripts\verify-global-playwright-mcp.ps1
codex mcp list
```

See `docs/PORTABLE-SETTINGS-BUNDLE.md` for the full setup guide, including
VS Code extensions, Continue personas, API keys, and Azure Copilot skills.

## Reading Order

```
 1. docs/01-MCP-MENTAL-MODEL.md              → Understand the architecture
 2. docs/PORTABLE-SETTINGS-BUNDLE.md          → All configs for another laptop
 3. docs/02-LOCAL-PLAYWRIGHT-LAB.md           → Practice locally
 4. docs/03-REMOTE-PLAYWRIGHT-LAB.md          → Deploy remote browser
 5. docs/04-KAGENT-INTEGRATION.md             → Future Kubernetes plans
 6. docs/GLOBAL-PLAYWRIGHT-MCP-PLAN.md        → Why per-host registration?
 7. docs/GLOBAL-PLAYWRIGHT-MCP-IMPLEMENTATION.md → How it was done
 8. docs/integrations/                        → AI tooling scaffold
 9. docs/TROUBLESHOOTING.md                   → When things break
```

## Key Concepts

### MCP Is Not Built Into Your Editor

Your editor (VS Code, Cursor) does **not** contain Playwright. It starts or
connects to a separate **MCP server** process, and that server controls the
browser. This separation is the single most important idea in this lab.

### No Cross-IDE MCP Registry

Each host reads its own config from its own path in its own format:

| Host | Config Path | Key Structure | Format |
|------|-------------|---------------|--------|
| VS Code | `%APPDATA%\Code\User\mcp.json` | `"servers"` | JSON |
| Cursor | `%USERPROFILE%\.cursor\mcp.json` | `"mcpServers"` | JSON |
| Codex | `%USERPROFILE%\.codex\config.toml` | `[mcp_servers.*]` | TOML |
| Continue | `%USERPROFILE%\.continue\config.yaml` | `mcpServers:` | YAML |

### Global = Per-Host Registration

When the lab says "global Playwright MCP," it means `playwright-global` is
registered at the **user level** in every host. There is no single OS setting.

## Version Matrix (Tested)

| Component | Version | Status |
|-----------|---------|--------|
| Windows | 10.0.26200 | CHECKED |
| Node.js | v23.0.0 | CHECKED |
| npm / npx | 10.9.0 | CHECKED |
| **Playwright MCP** | **0.0.76** (pinned) | CHECKED |
| VS Code | 1.125.1 | CHECKED |
| Cursor | 3.8.23 | CHECKED |
| Codex CLI | 0.141.0 | CHECKED |
| Continue | 2.0.0 | CHECKED |

## Directory Map

```
F:\Git\MCPtest\
├── .vscode\                → Workspace MCP, settings, extensions
├── config\                 → Tooling registries, placeholders
│   └── integrations\       → Azure MCP, Foundry placeholders
├── docs\                   → All documentation
│   ├── integrations\       → AI tooling scaffold docs
│   └── templates\          → Reusable MCP config templates
├── evidence\               → Validation records
│   ├── global\             → Global MCP evidence
│   ├── integrations\       → Tooling scaffold evidence
│   └── local\              → Playwright exercise evidence
├── scripts\                → Reusable PowerShell scripts
│   └── integrations\       → Scaffold verification scripts
└── server\                 → Docker deployment for remote browser
```

---

> **Last updated:** 2026-06-24
> **Source repo:** `F:\Git\MCPtest`
> **Remote:** `https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents`
