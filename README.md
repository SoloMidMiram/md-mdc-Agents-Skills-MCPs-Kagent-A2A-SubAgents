# MCP Agent Tooling Laboratory

[![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-2563EB)](#)
[![Playwright](https://img.shields.io/badge/Playwright-MCP_Server-45BA4B)](https://github.com/microsoft/playwright-mcp)
[![VS Code](https://img.shields.io/badge/VS_Code-Agent_MCP-007ACC)](#)
[![Cursor](https://img.shields.io/badge/Cursor-Agent_MCP-6C47FF)](#)
[![Codex CLI](https://img.shields.io/badge/Codex_CLI-Agent_MCP-000000)](#)
[![Continue](https://img.shields.io/badge/Continue-Agent_MCP-FF6B35)](#)
[![CI](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/workflows/quality.yml/badge.svg)](https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents/actions/workflows/quality.yml)

A complete **MCP (Model Context Protocol) developer tooling environment** —
browser automation, agent configurations, AI tools, and infrastructure templates
for VS Code, Cursor, Codex CLI, and Continue.

---

## Quick Start

```powershell
git clone https://github.com/SoloMidMiram/md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents.git
cd md-mdc-Agents-Skills-MCPs-Kagent-A2A-SubAgents
.\scripts\install-global-playwright-mcp.ps1
.\scripts\verify-global-playwright-mcp.ps1
codex mcp list   # → playwright-global (enabled)
```

**[→ Full setup guide](docs/PORTABLE-SETTINGS-BUNDLE.md)**
**[→ Introduction & manual](docs/GETTING-STARTED.md)**

---

## What's Inside

### 🤖 AI Agent Configurations

Portable agent configurations for every major MCP host:

| Host | What It Gets | Config Location |
|------|-------------|----------------|
| **VS Code Copilot** | 7 MCP servers (Playwright, GitHub, DevTools, markitdown, firecrawl, netdata, context7) | `%APPDATA%\Code\User\mcp.json` |
| **Cursor Agent** | Playwright MCP (`playwright-global`, `--isolated`) | `%USERPROFILE%\.cursor\mcp.json` |
| **Codex CLI** | Playwright MCP + sandbox rules | `%USERPROFILE%\.codex\config.toml` |
| **Continue** | 12 models, 8 agent personas, Playwright MCP, 4 global rules | `%USERPROFILE%\.continue\config.yaml` |

**[→ Portable settings bundle](docs/PORTABLE-SETTINGS-BUNDLE.md)** — Copy all configs to another laptop in 4 phases.

### 🧠 Agent Personas (Continue)

8 slash-command personas for structured AI collaboration:

| Command | Role | Purpose |
|---------|------|---------|
| `/orchestrator` | Planner | Goal decomposition, delegation, tracking |
| `/runner` | Executor | Code writing, tests, commands |
| `/documenter` | Writer | Documentation, ADRs, evidence |
| `/learner` | Analyst | Retrospectives, lesson extraction |
| `/planner` | Architect | Milestones, acceptance criteria |
| `/iterator` | Reviewer | Outcome review, regression detection |
| `/fullfeature` | Full-stack | 3-phase feature delivery |

### �— Browser Automation (Playwright MCP)

The `playwright-global` MCP server (`@playwright/mcp@0.0.76`, `--isolated`) is
registered at the **user level** in all 4 hosts — no per-project setup needed.

- **Safe tools:** `browser_navigate`, `browser_snapshot`, `browser_console_messages`, `browser_network_requests`, `browser_close`
- **Exercises:** 10 progressive labs in [`docs/02-LOCAL-PLAYWRIGHT-LAB.md`](docs/02-LOCAL-PLAYWRIGHT-LAB.md)
- **Remote browser:** Docker deployment with SSH tunnel ([`docs/03-REMOTE-PLAYWRIGHT-LAB.md`](docs/03-REMOTE-PLAYWRIGHT-LAB.md))

### �–️ Azure & Cloud Tooling

| Tool | State | Documentation |
|------|-------|---------------|
| Azure Resources for VS Code | ✅ Installed, dormant | `config/integrations/tooling-registry.yaml` |
| Azure MCP Server | ✅ Installed, dormant, read-only policy | `.vscode/settings.json` |
| Foundry Toolkit | ✅ Installed, local only | `config/integrations/foundry-cloud.placeholder.yaml` |
| 28 Azure Copilot Skills | ✅ Installed | `%USERPROFILE%\.agents\skills\` |

### 🔧 Infrastructure Templates

| Resource | Path | Purpose |
|----------|------|---------|
| Docker Compose | `server/compose.yaml` | Headless Chromium on Linux |
| SSH tunnel | `docs/03-REMOTE-PLAYWRIGHT-LAB.md` | Secure remote browser access |
| SSH concurrency fix | `docs/05-SSH-CONCURRENCY-FIX.md` | Multi-window VS Code Remote-SSH |
| Kubernetes / kagent | `docs/04-KAGENT-INTEGRATION.md` | Future cluster deployment |

### 📦 Config Templates (Portable)

| Template | For | Format |
|----------|-----|--------|
| `config/templates/vscode-user-mcp.json` | VS Code MCP | JSON |
| `config/templates/cursor-user-mcp.json` | Cursor MCP | JSON |
| `config/templates/codex-config.toml` | Codex CLI | TOML |
| `config/templates/continue-config.yaml` | Continue | YAML |

### 🔁 Reusable Scripts

| Script | Purpose |
|--------|---------|
| `scripts/install-global-playwright-mcp.ps1` | Register Playwright across 4 config targets (idempotent) |
| `scripts/verify-global-playwright-mcp.ps1` | Validate all registrations |
| `scripts/rollback-global-playwright-mcp.ps1` | Restore from timestamped backup |
| `scripts/evaluation/run-evaluation.ps1` | Run Pester evaluation suite (73 tests: 68 pass, 5 skip) |
| `scripts/integrations/inventory-tooling.ps1` | Report all tooling state |
| `scripts/integrations/verify-integration-scaffold.ps1` | Validate scaffold integrity |

### 🤖 CI Pipeline

| Workflow | Trigger | What It Does |
|----------|---------|-------------|
| `.github/workflows/quality.yml` | `push` / `pull_request` | Installs Codex CLI + Pester, verifies integration scaffold, runs evaluation suite (`windows-latest`, 30-min timeout) |

---

## Implementation Roadmap

> Fast-path policy: treat `Design only`, `Pending server`, `Placeholder`, and other explicitly deferred items as non-blocking. Keep them documented, but do not let production-polish work slow down correctness fixes, tests, or the current laptop-stable flow.

### Forward Order (Plan → Implementation)

| # | Phase | Plan Document | Implementation | Evidence | Status |
|---|-------|--------------|----------------|----------|--------|
| 1 | **MCP mental model** — architecture foundation | `docs/01-MCP-MENTAL-MODEL.md` | *(conceptual)* | — | ✅ Complete |
| 2 | **Local Playwright exercises** — 10 safe browser automation labs | `docs/02-LOCAL-PLAYWRIGHT-LAB.md` | *(exercise prompts)* | `evidence/local/exercise-*` | ✅ Complete |
| 3 | **Remote Docker deployment** — headless Chromium via SSH tunnel | `docs/03-REMOTE-PLAYWRIGHT-LAB.md` | `server/compose.yaml` (pinned `v0.0.76`, healthcheck, resource limits, security controls), `server/README.md` | — | ⏳ Needs Linux server |
| 4 | **SSH concurrency fix** — multi-window VS Code Remote-SSH repair | `docs/05-SSH-CONCURRENCY-FIX.md` | *(procedure doc)* | `memories/repo/ssh-concurrency-fix.md` | ✅ Complete |
| 5 | **Global Playwright MCP** — register `playwright-global` across 4 config targets / 5 runtime surfaces | `docs/GLOBAL-PLAYWRIGHT-MCP-PLAN.md` | `docs/GLOBAL-PLAYWRIGHT-MCP-IMPLEMENTATION.md`, `scripts/McpConfigTargets.ps1` (shared manifest + typed state model with DEPENDENCY_MISSING + TOML/YAML malformed detection), `scripts/install-global-playwright-mcp.ps1` (convergent + typed state detection + section-scoped YAML with generic key boundaries), `scripts/rollback-global-playwright-mcp.ps1` (round-trip), `scripts/verify-global-playwright-mcp.ps1` (exit-1 on failure), `scripts/evaluation/` (73 Pester tests: 68 pass, 5 skip, 0 fail — infrastructure + functional + production-path) | `evidence/global/` | ✅ PRODUCTION-PATH VERIFIED |
| 6 | **AI tooling integration scaffold** — Azure MCP, Foundry, Chat Eval | `docs/integrations/AI-TOOLING-INTEGRATION-PLAN.md` | `.vscode/settings.json`, `config/integrations/` | `evidence/integrations/` | ✅ AUDIT HARDENED |
| 7 | **Portable settings bundle** — capture user-level configs for new laptops | `docs/PORTABLE-SETTINGS-BUNDLE.md` | `config/templates/` | — | ✅ Complete |
| 8 | **Native VS Code agent customization** — `.instructions.md`, agents, prompts | *(recommended scaffold)* | `.github/instructions/`, `.github/agents/`, `.github/prompts/` | — | ✅ Implemented |
| 9 | **Python + K8s tool stack** — pyproject.toml, pre-commit, scripts, tasks | *(recommended scaffold)* | `pyproject.toml`, `.pre-commit-config.yaml`, `.vscode/tasks.json`, `scripts/quality/` | — | ✅ Implemented |
| 10 | **Project memory layer** — `.project-ai/memory/` with 7 knowledge domains | *(recommended scaffold)* | `.project-ai/memory/*.md`, `.project-ai/templates/*.md` | — | ✅ Implemented |
| 11 | **Dev container** — reproducible Linux dev environment (Node 23, PowerShell, Python, Docker, K8s) | *(recommended scaffold)* | `.devcontainer/devcontainer.json` | — | ✅ Implemented |
| 12 | **kagent / Kubernetes integration** — future cluster deployment | `docs/04-KAGENT-INTEGRATION.md` | *(design only)* | — | 📋 Design only |

### Reverse Order (Rollback)

To undo the entire setup in reverse:

| Step | Action | Relevant Files |
|------|--------|----------------|
| 12 | Stop any remote Docker browser | `server/`, `docker compose down` |
| 11 | Remove dev container | `.devcontainer/devcontainer.json` |
| 10 | Clear project memory (no Git side effects) | `.project-ai/memory/*` |
| 9 | Uninstall Python tools, remove pre-commit | `pyproject.toml`, `.pre-commit-config.yaml` |
| 8 | Remove VS Code agent customizations | `.github/instructions/`, `.github/agents/`, `.github/prompts/` |
| 7 | Delete portable config templates | `config/templates/` |
| 6 | Remove AI tooling scaffold (settings, placeholders) | `.vscode/settings.json`, `config/integrations/` |
| 5 | **Unregister `playwright-global`** from all hosts | `.\scripts\rollback-global-playwright-mcp.ps1 -BackupDir <dir>` (preferred) or `codex mcp remove playwright-global` + edit `%APPDATA%\Code\User\mcp.json` + edit `%USERPROFILE%\.cursor\mcp.json` + edit `%USERPROFILE%\.continue\config.yaml` |
| 4 | Restore default SSH MaxStartups | `/etc/ssh/sshd_config` (server-side) |
| 3 | Remove server deployment files | `server/` |
| 2 | Delete exercise evidence | `evidence/local/` |
| 1 | Archive docs (or keep as reference) | `docs/` |

### Plan → Implementation Index

| Plan Document | Implementation | Evidence | Status |
|---------------|---------------|----------|--------|
| `docs/GLOBAL-PLAYWRIGHT-MCP-PLAN.md` | `docs/GLOBAL-PLAYWRIGHT-MCP-IMPLEMENTATION.md` + `scripts/McpConfigTargets.ps1` (shared manifest) + `scripts/install-global-playwright-mcp.ps1` (convergent) + `scripts/rollback-global-playwright-mcp.ps1` (round-trip) + `scripts/verify-global-playwright-mcp.ps1` (exit-1) | `evidence/global/` — 9 files | ✅ Verified |
| `docs/integrations/AI-TOOLING-INTEGRATION-PLAN.md` | `.vscode/settings.json` (Azure MCP policy) + `config/integrations/tooling-registry.yaml` | `evidence/integrations/` — 3 files | ✅ Audited |
| `docs/03-REMOTE-PLAYWRIGHT-LAB.md` | `server/compose.yaml` + `server/README.md` | `evidence/remote/.gitkeep` | ⏳ Pending server |
| `docs/04-KAGENT-INTEGRATION.md` | *(design only — no implementation started)* | — | 📋 Future |
| `docs/PORTABLE-SETTINGS-BUNDLE.md` | `config/templates/` (4 templates) | — | ✅ Complete |
| `docs/01-MCP-MENTAL-MODEL.md` | *(conceptual — no code artifact)* | — | ✅ Complete |
| `docs/02-LOCAL-PLAYWRIGHT-LAB.md` | *(exercise prompts — run in agent)* | `evidence/local/` — 8 files | ✅ Complete |
| `docs/05-SSH-CONCURRENCY-FIX.md` | *(procedure doc)* | `memories/repo/ssh-concurrency-fix.md` | ✅ Complete |

---

## Version Matrix

| Component | Version | Status |
|-----------|---------|--------|
| Node.js | v23.0.0 | ✅ CHECKED |
| Playwright MCP | **0.0.76** (pinned) | ✅ CHECKED |
| VS Code | 1.125.1 | ✅ CHECKED |
| Cursor | 3.8.23 | ✅ CHECKED |
| Codex CLI | 0.141.0 | ✅ CHECKED |
| Continue | 2.0.0 | ✅ CHECKED |
| Windows | 10.0.26200 | ✅ CHECKED |

---

## Repository Map

```
.
├── .devcontainer/              → Reproducible Linux dev environment
├── .github/
│   ├── copilot-instructions.md → Repository-wide rules
│   ├── instructions/           → File-pattern rules (Python, K8s, tests, security, docs)
│   ├── prompts/                → Reusable agent prompts (quality, diagnosis, review, memory)
│   ├── agents/                 → Custom agents (Python reviewer, K8s reviewer, release auditor)
│   └── workflows/
│       └── quality.yml         → CI: evaluation suite + scaffold verification
├── .project-ai/
│   ├── memory/                 → Durable project memory (7 knowledge domains)
│   └── templates/              → Incident and decision templates
├── .vscode/
│   ├── extensions.json         → 14 extension recommendations
│   ├── settings.json           → Python, K8s, Azure MCP config
│   └── tasks.json              → 6 quality gate tasks
├── config/
│   ├── integrations/           → Tooling registries, placeholders
│   └── templates/              → 📤 Portable config templates (4 hosts)
├── docs/
│   ├── GETTING-STARTED.md      → �— Introduction & manual
│   ├── PORTABLE-SETTINGS-BUNDLE.md → �— Portable settings for new laptops
│   ├── 01-MCP-MENTAL-MODEL.md  → MCP architecture concepts
│   ├── 02-LOCAL-PLAYWRIGHT-LAB.md → 10 browser automation exercises
│   ├── 03-REMOTE-PLAYWRIGHT-LAB.md → Docker + SSH tunnel
│   ├── 04-KAGENT-INTEGRATION.md → Kubernetes/kagent design
│   ├── 05-SSH-CONCURRENCY-FIX.md → SSH MaxStartups repair
│   ├── GLOBAL-PLAYWRIGHT-MCP-PLAN.md → Architecture & strategy
│   ├── GLOBAL-PLAYWRIGHT-MCP-IMPLEMENTATION.md → Implementation details
│   ├── integrations/           → AI tooling scaffold docs
│   ├── templates/              → MCP config templates
│   └── TROUBLESHOOTING.md      → Common issues & fixes
├── evidence/
│   ├── global/                 → Global MCP validation (9 files)
│   ├── integrations/           → Tooling scaffold evidence (3 files)
│   └── local/                  → Playwright exercise evidence (8 files)
├── scripts/
│   ├── install-global-playwright-mcp.ps1
│   ├── verify-global-playwright-mcp.ps1
│   ├── rollback-global-playwright-mcp.ps1
│   ├── evaluation/             → Pester-based evaluation framework (73 tests: 68 pass, 5 skip)
│   ├── integrations/           → Inventory & verify scripts
│   ├── kubernetes/validate.ps1
│   ├── quality/                → Python quality gate scripts
│   └── security/scan.ps1
└── server/                     → Docker deployment for remote browser
```

---

## Reading Order

```
 1. docs/GETTING-STARTED.md                       → Start here
 2. docs/01-MCP-MENTAL-MODEL.md                   → Understand MCP architecture
 3. docs/PORTABLE-SETTINGS-BUNDLE.md               → Set up another laptop
 4. docs/02-LOCAL-PLAYWRIGHT-LAB.md                → Practice locally
 5. docs/03-REMOTE-PLAYWRIGHT-LAB.md               → Deploy remote browser
 6. docs/GLOBAL-PLAYWRIGHT-MCP-PLAN.md             → Global MCP architecture
 7. docs/GLOBAL-PLAYWRIGHT-MCP-IMPLEMENTATION.md   → Implementation details
 8. docs/integrations/AI-TOOLING-INTEGRATION-PLAN.md → Tooling scaffold
 9. docs/04-KAGENT-INTEGRATION.md                  → Future Kubernetes plans
10. docs/TROUBLESHOOTING.md                        → Reference when stuck
```

---

## Key Concepts

**MCP is not built into your editor.** Your editor starts or connects to a
separate MCP server process. The server controls the browser, not the editor.

**No cross-IDE MCP registry.** Each host has its own config in its own format:

| Host | Key Structure | Format |
|------|---------------|--------|
| VS Code | `"servers"."*"` | JSON |
| Cursor | `"mcpServers"."*"` | JSON |
| Codex | `[mcp_servers.*]` | TOML |
| Continue | `mcpServers[].name` | YAML |

**Global = per-host.** "Global" means registered at user level in every host.

**Every plan has an implementation.** Each `docs/*PLAN*.md` maps to a
corresponding `docs/*IMPLEMENTATION*.md` or `scripts/` artifact, with
evidence recorded under `evidence/`.

---

## License

MIT — see [LICENSE](LICENSE).

---

*Last updated: 2026-06-25*

---

## �’ Comprehension Quiz

Test whether you understand the foundational MCP concepts before proceeding:

**Q1:** What component is the MCP host, and what component is the MCP server?  
**Q2:** What is the difference between STDIO transport and HTTP transport?  
**Q3:** Where does the browser process actually run — on the MCP host machine or the MCP server machine?  
**Q4:** Why does `localhost` mean different things on your laptop vs. a server vs. a container vs. a Kubernetes pod?  
**Q5:** Why must an MCP endpoint never be exposed publicly without authentication or network protection?

*Answers are found in `docs/01-MCP-MENTAL-MODEL.md` and `docs/02-LOCAL-PLAYWRIGHT-LAB.md`.*
