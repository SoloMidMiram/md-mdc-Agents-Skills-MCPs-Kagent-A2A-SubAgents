# Portable Agents–Skills–MCPs Settings Bundle

> **Purpose:** Capture every user-level configuration from this development machine
> so you can reproduce the same agent/MCP environment on another laptop.
>
> **Source machine:** `C:\Users\cebit.ir` (Windows)
> **Target:** Any Windows laptop with VS Code, Cursor, Codex, and Continue

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [VS Code User MCP Servers](#2-vs-code-user-mcp-servers)
3. [Cursor MCP & Settings](#3-cursor-mcp--settings)
4. [Codex CLI Configuration](#4-codex-cli-configuration)
5. [Continue Configuration](#5-continue-configuration)
6. [Continue Slash-Command Personas](#6-continue-slash-command-personas)
7. [Continue Global Rules](#7-continue-global-rules)
8. [Azure Copilot Skills](#8-azure-copilot-skills)
9. [VS Code Extension Bundle](#9-vs-code-extension-bundle)
10. [Quick-Install Scripts](#10-quick-install-scripts)
11. [Installation Order for a New Laptop](#11-installation-order-for-a-new-laptop)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      YOUR LAPTOP                         │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌─────────┐   │
│  │VS Code   │  │ Cursor   │  │ Codex  │  │ Continue│   │
│  │Copilot   │  │ Agent    │  │ CLI    │  │(VS/Cursor)│  │
│  └────┬─────┘  └────┬─────┘  └───┬────┘  └────┬────┘   │
│       │              │            │            │        │
│       ▼              ▼            ▼            ▼        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  playwright-global  (npx @playwright/mcp)        │   │
│  │  --isolated  |  @playwright/mcp@0.0.76           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Additional MCP servers (VS Code only):            │   │
│  │  markitdown, netdata, context7, chrome-devtools,  │   │
│  │  github-mcp, firecrawl                            │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Key principle:** Each agent host has its own independent MCP configuration.
There is no single OS-level MCP registry.

---

## 2. VS Code User MCP Servers

**File:** `%APPDATA%\Code\User\mcp.json`

Uses `"servers"` key (not `"mcpServers"` like Cursor).

| Server | Type | Command / URL | Purpose |
|--------|------|---------------|---------|
| `microsoft/markitdown` | stdio | `uvx markitdown-mcp@0.0.1a4` | Doc-to-Markdown |
| `io.github.netdata/mcp-server` | http | `https://app.netdata.cloud/api/v1/mcp` | Monitoring (needs token) |
| `io.github.upstash/context7` | stdio | `npx @upstash/context7-mcp@1.0.31` | Search (needs key) |
| `io.github.ChromeDevTools/chrome-devtools-mcp` | stdio | `npx chrome-devtools-mcp@0.21.0` | Chrome DevTools |
| `io.github.github/github-mcp-server` | http | `https://api.githubcopilot.com/mcp/` | GitHub API |
| `firecrawl/firecrawl-mcp-server` | stdio | `npx firecrawl-mcp@latest` | Web scraping (needs key) |
| **`playwright-global`** | stdio | `npx -y @playwright/mcp@0.0.76 --isolated` | Browser automation |

### Template Entry for `mcp.json`

```json
{
    "servers": {
        "playwright-global": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@playwright/mcp@0.0.76", "--isolated"]
        }
    }
}
```

---

## 3. Cursor MCP & Settings

**File:** `%USERPROFILE%\.cursor\mcp.json`

```json
{
    "mcpServers": {
        "playwright-global": {
            "command": "npx",
            "args": ["-y", "@playwright/mcp@0.0.76", "--isolated"]
        }
    }
}
```

> **Cursor uses `"mcpServers"`** (not `"servers"` like VS Code). This is a common trap.

### Cursor Settings

**File:** `%USERPROFILE%\.cursor\settings.json`

```json
{
    "http.proxy": "http://127.0.0.1:8080",
    "https.proxy": "http://127.0.0.1:8080",
    "http.proxyStrictSSL": false
}
```

> Only needed if your network requires a proxy. Adjust or omit on the target laptop.

---

## 4. Codex CLI Configuration

**File:** `%USERPROFILE%\.codex\config.toml`

```toml
model = "gpt-5.4-mini"
model_reasoning_effort = "medium"
personality = "pragmatic"
service_tier = "default"

[windows]
sandbox = "elevated"

[mcp_servers.playwright-global]
command = "npx"
args = ["-y", "@playwright/mcp@0.0.76", "--isolated"]
```

### Codex Sandbox Rules

**File:** `%USERPROFILE%\.codex\rules\default.rules`

A prefix-allowlist for safe command execution. Copy from source machine
and adjust for the target.

---

## 5. Continue Configuration

**File:** `%USERPROFILE%\.continue\config.yaml`

### Models (API Keys Required)

| Model | Provider | Key Needed |
|-------|----------|------------|
| DeepSeek Chat / Reasoner | OpenAI | `DEEPSEEK_API_KEY` |
| GPT-4.1 / Mini / 4o / Mini | OpenAI | `OPENAI_API_KEY` |
| gpt-oss:20b, qwen3, deepseek-r1, Gemma3 | Ollama (local) | No |

### MCP Server Entry

```yaml
mcpServers:
  - name: playwright-global
    type: stdio
    command: npx
    args:
      - "-y"
      - "@playwright/mcp@0.0.76"
      - "--isolated"
```

### Secrets

**File:** `%USERPROFILE%\.continue\secrets.json`

```json
{
    "DEEPSEEK_API_KEY": "sk-...",
    "OPENAI_API_KEY": "sk-..."
}
```

> **Do not commit secrets to Git.** Copy them manually to the new laptop.

---

## 6. Continue Slash-Command Personas

8 slash-command personas defined in `config.yaml` under `slashCommands:`:

| Command | Role | Purpose |
|---------|------|---------|
| `/personas` | Index | Lists all available personas |
| `/orchestrator` | Planner | Goal decomposition, delegation, tracking |
| `/runner` | Executor | Code writing, tests, platform commands |
| `/documenter` | Writer | Knowledge capture, documentation |
| `/learner` | Analyst | Retrospectives, lesson extraction |
| `/planner` | Architect | Milestone planning, acceptance criteria |
| `/iterator` | Reviewer | Outcome review, regression detection |
| `/fullfeature` | Full-stack | 3-phase end-to-end feature delivery |

> These are **portable**. Copy `config.yaml` to the new laptop's
> `%USERPROFILE%\.continue\` directory.

---

## 7. Continue Global Rules

**Directory:** `%USERPROFILE%\.continue\rules\`

| File | Purpose |
|------|---------|
| `global-edit-error-troubleshooting.md` | Stop cascading edits after syntax errors |
| `global-post-edit-syntax-verification.md` | Verify Python syntax after every edit |
| `global-powershell-python-quoting.md` | Write temp files instead of inline Python |
| `global-secrets-and-logs.md` | Never print, store, or commit secrets |

> Copy the entire `rules\` directory to the new laptop.

---

## 8. Azure Copilot Skills

**Directory:** `%USERPROFILE%\.agents\skills\`

28 Azure Copilot skills installed from `microsoft/azure-skills`:

| Domain | Skills |
|--------|--------|
| **Compute & AKS** | `airunway-aks-setup`, `azure-compute`, `azure-kubernetes` |
| **AI & Foundry** | `azure-ai`, `azure-aigateway`, `azure-hosted-copilot-sdk`, `microsoft-foundry` |
| **Migration** | `azure-cloud-migrate`, `azure-upgrade` |
| **DevOps & Deploy** | `azure-deploy`, `azure-prepare`, `azure-validate` |
| **Monitoring** | `appinsights-instrumentation`, `azure-diagnostics`, `azure-kusto`, `azure-messaging` |
| **Security** | `azure-compliance`, `azure-rbac`, `entra-agent-id`, `entra-app-registration` |
| **Storage & Data** | `azure-storage`, `azure-quotas` |
| **Cost & Resources** | `azure-cost`, `azure-resource-lookup`, `azure-resource-visualizer` |
| **Reliability & Infra** | `azure-reliability`, `azure-enterprise-infra-planner` |

**Install on a new laptop:** Requires VS Code with Copilot Agent framework.
Skills are managed automatically through the `.agents` framework or
installed from `https://github.com/microsoft/azure-skills`.

---

## 9. VS Code Extension Bundle

The workspace recommendation list is the source of truth for editor
extensions:

**File:** `F:\Git\MCPtest\.vscode\extensions.json`

```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "ms-python.debugpy",
        "ms-python.mypy-type-checker",
        "ms-azuretools.vscode-azureresourcegroups",
        "ms-azuretools.vscode-azure-mcp-server",
        "ms-windows-ai-studio.windows-ai-studio",
        "ms-kubernetes-tools.vscode-kubernetes-tools",
        "redhat.vscode-yaml",
        "ms-azuretools.vscode-containers",
        "ms-vscode-remote.remote-containers",
        "ms-vscode-remote.remote-ssh",
        "github.vscode-github-actions"
    ]
}
```

For the default Python profile, install the repo's Python/Ruff bundle:

```powershell
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
code --install-extension ms-python.debugpy
code --install-extension ms-python.mypy-type-checker
```

---

## 10. Quick-Install Scripts

The repository includes reusable PowerShell scripts:

| Script | Purpose |
|--------|---------|
| `scripts/install-global-playwright-mcp.ps1` | Register Playwright across all 4 hosts |
| `scripts/verify-global-playwright-mcp.ps1` | Validate all registrations |
| `scripts/rollback-global-playwright-mcp.ps1` | Restore from named backup |
| `scripts/integrations/inventory-tooling.ps1` | Report all tooling state |

---

## 11. Installation Order for a New Laptop

### Phase 1 — Prerequisites

```powershell
# Install Node.js >= 18
winget install OpenJS.NodeJS.LTS

# Install editors
winget install Microsoft.VisualStudioCode
# Download Cursor from https://cursor.sh
npm install -g @openai/codex

# Install Python 3.12 and uv (required by the workspace tooling)

# Optional: install non-Python workspace extensions one-by-one or let VS Code
# prompt from .vscode\extensions.json when the workspace opens.
```

### Phase 2 — MCP Configuration

Copy these files from this bundle (or from your timestamped backup):

| Source | Destination |
|--------|-------------|
| `config/templates/vscode-user-mcp.json` | `%APPDATA%\Code\User\mcp.json` |
| `config/templates/cursor-user-mcp.json` | `%USERPROFILE%\.cursor\mcp.json` |
| `config/templates/codex-config.toml` | `%USERPROFILE%\.codex\config.toml` |
| `config/templates/continue-config.yaml` | `%USERPROFILE%\.continue\config.yaml` |
| (from backup) | `%USERPROFILE%\.continue\rules\*` |
| (manual) | `%USERPROFILE%\.continue\secrets.json` |

Then run:

```powershell
cd F:\Git\MCPtest
.\scripts\install-global-playwright-mcp.ps1
.\scripts\verify-global-playwright-mcp.ps1
codex mcp list
```

### Phase 3 — Validation

```powershell
codex exec "Use playwright-global. browser_navigate to https://example.com. browser_snapshot. browser_close."
```

### Phase 4 — Agent Skills

Azure Copilot skills auto-install through the `.agents` framework
when VS Code detects the `microsoft/azure-skills` manifest.

---

## Appendix: Config File Reference

| Host | Config Path | Key Structure | Format |
|------|------------|---------------|--------|
| VS Code (user) | `%APPDATA%\Code\User\mcp.json` | `"servers"."playwright-global"` | JSON |
| Cursor (user) | `%USERPROFILE%\.cursor\mcp.json` | `"mcpServers"."playwright-global"` | JSON |
| Codex (user) | `%USERPROFILE%\.codex\config.toml` | `[mcp_servers.playwright-global]` | TOML |
| Continue (user) | `%USERPROFILE%\.continue\config.yaml` | `mcpServers[].name` | YAML |
| Continue rules | `%USERPROFILE%\.continue\rules\` | Individual `.md` files | Markdown |
| Continue secrets | `%USERPROFILE%\.continue\secrets.json` | API key pairs | JSON |
| Azure skills | `%USERPROFILE%\.agents\skills\` | Per-skill `SKILL.md` | Markdown |
| Cursor settings | `%USERPROFILE%\.cursor\settings.json` | Proxy configuration | JSON |
| Codex sandbox rules | `%USERPROFILE%\.codex\rules\default.rules` | Command allowlist | TOML |

---

> **Last updated:** 2026-06-24
> **Source repo:** `F:\Git\MCPtest` (branch: `main`)
> **Remote:** `https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents`
