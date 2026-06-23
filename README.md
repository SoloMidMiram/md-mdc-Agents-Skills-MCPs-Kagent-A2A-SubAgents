# Playwright MCP Laboratory

This laboratory contains documentation and configuration to learn and deploy Microsoft's Playwright MCP browser automation system in staged environments.

## Overview
This project guides you through:
- Local visible browser automation using Playwright MCP
- Installation and validation in the Codex IDE
- Configuring Cursor and VS Code to use the Playwright MCP server
- Docker-based Linux server deployment for headless Chromium
- Secure remote access via SSH tunnels
- Future integration with Kubernetes using kagent
- **Infrastructure:** SSH concurrency diagnostics and repair for the remote lab server

## Roadmap
The laboratory consists of progressive phases with clear prerequisites:

1. **Environment inspection:** Verify local environment meets requirements including Node.js >= 18.
2. **Local lab repository setup:** Create a clean folder with docs, server configs, and evidence subfolders.
3. **Playwright MCP setup in Codex:** Add an MCP server configuration using exact tested Playwright MCP version.
4. **Local tool validation in Codex:** Run safe browser automation tasks and validate tool responses.
5. **Cursor configuration:** Add MCP server details to Cursor configs while preserving existing settings.
6. **VS Code integration:** Add MCP server config to VS Code workspace with appropriate profiles.
7. **Local learning exercise documentation:** Write exercises for safe navigation, diagnostics, failures, and troubleshooting.
8. **Version pinning and matrix creation:** Record tested versions for reproducibility.
9. **Linux server Docker deployment prep:** Prepare Docker Compose deployment with security best practices.
10. **SSH tunnel documentation:** Document secure remote access to server MCP endpoint.
11. **SSH concurrency fix:** Diagnose and repair multi-window VS Code Remote-SSH limitation (`docs/05-SSH-CONCURRENCY-FIX.md`).
12. **Future kagent integration:** Outline Kubernetes-based deployment options and MCP usage.
13. **Troubleshooting matrix:** Document common issues, symptoms, diagnostics, and safe repairs.

## Safety and Operating Rules
- No Kubernetes setup until local and Docker stages are validated.
- Use npx with pinned Playwright MCP version for consistent results.
- Do not globally install MCP or Playwright packages unnecessarily.
- Keep local, remote, and Kubernetes stages clearly separated.
- Do not expose MCP ports publicly without appropriate protection.
- Never submit forms or modify live data during tests.

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Repository cleanup & organization | ✅ Complete |
| 1 | Environment re-verification | ✅ Complete |
| 2 | Codex MCP registration | ✅ Complete |
| 3 | Cursor MCP configuration | ✅ Complete |
| 4 | VS Code MCP configuration | ✅ Complete |
| 5 | Local learning exercises (1-10) | ✅ Complete |
| 6 | Server deployment docs finalized | ✅ Complete |
| 7 | Server deployment & SSH tunnel | ⏳ Needs Linux server |
| 8 | kagent integration | 📋 Design only |

## Final Verification
Successful lab completion requires:
- Successful local visible browser test with Codex.
- Independent validation of Cursor and VS Code configurations.
- Fully documented lab exercises and troubleshooting.
- Prepared but not executed server and Kubernetes deployment files.

# Reverse Roadmap
For rollback or audit, the reverse flow is:
- Stop and remove any running server or container.
- Remove MCP server entries from Codex, Cursor, and VS Code configurations.
- Delete the local lab folders and evidence.
- Unpin Playwright MCP versions if testing newer releases.

# Contributions
Contributions are welcome as issues or pull requests, especially for documentation improvements and extended troubleshooting cases.

# License
This project is provided under MIT license.

---

## 📋 Version Matrix

| Component               | Version          | Validation Status |
|-------------------------|------------------|-------------------|
| Operating System        | Windows 10.0.26200 | CHECKED          |
| PowerShell Version      | 5.1.26100.8655   | CHECKED           |
| Node.js                 | v23.0.0          | CHECKED           |
| npm                     | 10.9.0           | CHECKED           |
| npx                     | 10.9.0           | CHECKED           |
| Playwright MCP          | 0.0.76           | CHECKED           |
| Git                     | 2.45.2.windows.1 | CHECKED           |
| Codex CLI               | 0.141.0          | CHECKED           |
| Cursor MCP config       | —                | PASS              |
| VS Code MCP config      | —                | PASS              |
| Local browser test      | —                | PASS              |
| Local exercises (1-10)  | —                | PASS              |
| Server deployment       | —                | NOT RUN           |
| kagent integration      | —                | FUTURE (design)   |

*Last tested: 2026-06-23 (Phase 1 re-verification)*

---

## 🔄 Reverse Roadmap (Rollback Procedure)

If you need to undo the entire laboratory setup:

1. **Stop servers:**
   ```powershell
   cd /opt/playwright-mcp && docker compose down
   ```
2. **Remove MCP server entries:**
   ```powershell
   codex mcp remove playwright-local
   codex mcp remove playwright-remote
   ```
3. **Delete Cursor MCP config entry** (edit `%USERPROFILE%\.cursor\mcp.json`)
4. **Delete VS Code MCP config entry** (edit `.vscode/mcp.json`)
5. **Remove lab directory:**
   ```powershell
   Remove-Item -Recurse -Force $HOME\playwright-mcp-lab
   ```
6. **Optionally remove cached profiles:**
   ```powershell
   Remove-Item -Recurse -Force "$env:LOCALAPPDATA\ms-playwright\codex-mcp-profile"
   Remove-Item -Recurse -Force "$env:LOCALAPPDATA\ms-playwright\cursor-mcp-profile"
   Remove-Item -Recurse -Force "$env:LOCALAPPDATA\ms-playwright\vscode-mcp-profile"
   ```
7. **Restore backed-up configs** if needed.
8. **Unpin version:** Future tests can use `@playwright/mcp@latest` again.

---

## ✅ Final Verification Report

### 📁 Files Created or Changed (Repository)
- `README.md` — Roadmap, implementation status, version matrix, verification report
- `docs/01-MCP-MENTAL-MODEL.md` — Conceptual foundation
- `docs/02-LOCAL-PLAYWRIGHT-LAB.md` — Local learning exercises
- `docs/03-REMOTE-PLAYWRIGHT-LAB.md` — Remote/SSH tunnel documentation
- `docs/04-KAGENT-INTEGRATION.md` — Future kagent design
- `docs/05-SSH-CONCURRENCY-FIX.md` — SSH multi-window concurrency repair
- `docs/TROUBLESHOOTING.md` — Troubleshooting matrix
- `docs/archive/playwrightraw.md` — Raw execution plan (archived from root)
- `docs/templates/mcp-vscode.json` — VS Code MCP config template
- `docs/templates/mcp-cursor.json` — Cursor MCP config template
- `docs/templates/compose.yaml` — Standalone Docker Compose template
- `server/compose.yaml` — Docker Compose configuration
- `server/env-example.txt` — Environment variable template
- `server/README.md` — Server deployment commands (updated with SCP transfer)
- `.gitignore` — Sensitive file exclusions

---

## 📚 Documentation Map

```
docs/
├── 01-MCP-MENTAL-MODEL.md          # Core concepts: MCP architecture
├── 02-LOCAL-PLAYWRIGHT-LAB.md      # Local browser automation exercises
├── 03-REMOTE-PLAYWRIGHT-LAB.md     # Remote server deployment via SSH
├── 04-KAGENT-INTEGRATION.md        # Future Kubernetes/kagent plans
├── 05-SSH-CONCURRENCY-FIX.md       # 🆕 SSH MaxStartups concurrency repair
├── TROUBLESHOOTING.md              # Common issues and solutions
├── archive/                        # Historical/archived documents
│   └── playwrightraw.md
└── templates/                      # Configuration templates
    ├── compose.yaml
    ├── mcp-cursor.json
    └── mcp-vscode.json

evidence/                           # Test evidence (local/remote)
server/                             # Docker deployment configs
```

### Reading Order

```
1. 01-MCP-MENTAL-MODEL.md          ──→ Understand the architecture
2. 02-LOCAL-PLAYWRIGHT-LAB.md      ──→ Practice locally first
3. 05-SSH-CONCURRENCY-FIX.md       ──→ Ensure reliable remote access
4. 03-REMOTE-PLAYWRIGHT-LAB.md     ──→ Deploy and test remotely
5. 04-KAGENT-INTEGRATION.md        ──→ Plan Kubernetes deployment
6. TROUBLESHOOTING.md              ──→ Reference when stuck
```
- `docs/04-KAGENT-INTEGRATION.md` — Future kagent design
- `docs/TROUBLESHOOTING.md` — Troubleshooting matrix
- `docs/archive/playwrightraw.md` — Raw execution plan (archived)
- `docs/templates/mcp-vscode.json` — VS Code MCP config template
- `docs/templates/mcp-cursor.json` — Cursor MCP config template
- `docs/templates/compose.yaml` — Standalone Docker Compose template
- `server/compose.yaml` — Docker Compose configuration
- `server/env-example.txt` — Environment variable template
- `server/README.md` — Server deployment commands
- `.gitignore` — Sensitive file exclusions
- `evidence/local/.gitkeep` — Placeholder
- `evidence/remote/.gitkeep` — Placeholder

### � Files Created or Changed (Local — gitignored)
- `.vscode/mcp.json` — VS Code MCP server config (STDIO, playwright-local)
- `%USERPROFILE%\.cursor\mcp.json` — Cursor MCP server config (STDIO, playwright-local)

### 📂 Backups Created
- None (no pre-existing configs were modified — all were created fresh)

### 🧪 Commands Executed (Implementation Phase)
- `codex mcp add playwright-local -- npx -y "@playwright/mcp@0.0.76" --user-data-dir "$env:USERPROFILE\AppData\Local\ms-playwright\codex-mcp-profile"`
- `codex mcp list` — verified: `playwright-local` enabled
- VS Code: `browser_navigate` → https://example.com — SUCCESS
- VS Code: `browser_getAccessibilitySnapshot` — structured tree returned
- VS Code: Safe click → IANA page → `goBack` — round-trip SUCCESS
- VS Code: Console messages — 0 errors, 0 warnings (clean page)
- VS Code: Network inspection — 1 request, 200 OK
- VS Code: Element-not-found → Timeout 10000ms error
- VS Code: Closed port → `net::ERR_CONNECTION_REFUSED`
- VS Code: DNS failure → Timeout 10000ms (DNS layer)
- VS Code: Browser IP → `46.151.26.41` (laptop IP confirmed)

### 🔢 Exact Versions Discovered
- Node.js: v23.0.0
- npm: 10.9.0
- npx: 10.9.0
- Playwright MCP: 0.0.76
- Codex CLI: 0.141.0 (installed via `npm install -g @openai/codex`)
- Git: 2.45.2.windows.1
- OS: Windows 10.0.26200

### ✅ Tests Passed
- ✅ Environment inspection (Node >= 18, npm, npx, git, codex all present)
- ✅ Playwright MCP package version check (`npm view`)
- ✅ Playwright MCP CLI help (`npx @playwright/mcp@0.0.76 --help`)
- ✅ Codex MCP registration (`codex mcp add playwright-local`)
- ✅ VS Code browser validation (all 10 exercises passed)
- ✅ Cursor MCP config created (`%USERPROFILE%\.cursor\mcp.json`)
- ✅ Exercise 1: Read-Only Navigation
- ✅ Exercise 2: Accessibility Structure Inspection
- ✅ Exercise 3: Safe Clicking and Navigation
- ✅ Exercise 4: Console Error Inspection
- ✅ Exercise 5: Network Request Inspection
- ✅ Exercise 6: Persistent Profile vs --isolated
- ✅ Exercise 7: Element-Not-Found Failure
- ✅ Exercise 8: Navigation Timeout
- ✅ Exercise 9: DNS Failure
- ✅ Exercise 10: Browser IP Comparison

### ⏳ Tests Pending
- ⏳ Codex browser validation (needs new Codex session)
- ⏳ Cursor browser validation (needs Cursor restart to load MCP)
- ⏳ Server Docker deployment (needs Linux server)
- ⏳ SSH tunnel test (needs Linux server)
- ⏳ Remote browser validation (needs Linux server)
- 📋 kagent integration (future — design only)

### 🚫 Configuration Changes Deliberately Not Made
- No edits to `~/.codex/config.toml` (MCP was added via `codex mcp add` CLI instead)
- No global npm installations of @playwright/mcp (always via npx)
- No Windows Firewall modifications (no HTTP MCP server running locally)
- No SSH connection was initiated
- No server commands were executed from Windows
- No edits to `.vscode/mcp.json`
- No Windows Firewall modifications
- No SSH connection was initiated
- No server commands were executed from Windows

### ✅ Configuration Changes Made
- `npm install -g @openai/codex` — Installed Codex CLI (required for `codex mcp add`)

### 🔒 Security Decisions
- All future server deployments bound to 127.0.0.1 only
- No public exposure of MCP endpoints
- No credentials, cookies, or secrets in version control
- No form submission or data modification during tests
- No `--ignore-https-errors` unless explicitly justified
- No Docker socket mounts
- No privileged containers

### 👣 Implementation Progress

| Step | Status |
|------|--------|
| Phase 0: Repo cleanup | ✅ Complete |
| Phase 1: Environment re-verification | ✅ Complete |
| Phase 2: Codex MCP integration | 🔄 In progress |
| Phase 3: Cursor MCP configuration | ⏳ Pending |
| Phase 4: VS Code MCP configuration | ⏳ Pending |
| Phase 5: Local learning exercises | ⏳ Pending |
| Phase 6: Server deployment prep | ⏳ Pending |
| Phase 7: Server deploy & SSH tunnel | ⏳ Requires Linux server |
| Phase 8: kagent integration | 🔮 Future (design doc only) |

---

## 📝 Comprehension Quiz

Test whether you understand the foundational MCP concepts before proceeding:

**Q1:** What component is the MCP host, and what component is the MCP server?  
**Q2:** What is the difference between STDIO transport and HTTP transport?  
**Q3:** Where does the browser process actually run — on the MCP host machine or the MCP server machine?  
**Q4:** Why does `localhost` mean different things on your laptop vs. a server vs. a container vs. a Kubernetes pod?  
**Q5:** Why must an MCP endpoint never be exposed publicly without authentication or network protection?

*Answers are found in `docs/01-MCP-MENTAL-MODEL.md` and `docs/02-LOCAL-PLAYWRIGHT-LAB.md`.*