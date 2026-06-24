# Global Playwright MCP Implementation Plan

## 1. Goal and Non-Goals

**Goal:** Register a single `playwright-global` MCP server (pinned `@playwright/mcp@0.0.76`, `--isolated`) as a user-level tool for every local MCP host on this machine:

1. VS Code native GitHub Copilot agent
2. Cursor native agent
3. Codex CLI
4. Continue inside VS Code
5. Continue inside Cursor

**Non-Goals:**
- No Docker deployment
- No HTTP MCP transport
- No Kubernetes/kagent changes
- No remote server configuration
- No package version upgrade
- No browser-profile migration
- No shared cross-IDE MCP registry (no such thing exists)

## 2. Why No Single Cross-IDE Global MCP Registry

Each IDE/agent defines its own MCP configuration in its own format:
- **VS Code**: `servers` key in `mcp.json`, supports `"type": "stdio"` and `"type": "http"`
- **Cursor**: `mcpServers` key in `mcp.json`, `command`/`args` structure
- **Codex**: TOML `[mcp_servers.*]` sections in `config.toml`
- **Continue**: YAML `mcpServers:` list in `config.yaml` or standalone files under `.continue/mcpServers/`

There is no OS-level MCP registry. Global availability must be implemented per host.

## 3. Host-by-Host Architecture

| Host | Config Format | Config Path | Key Structure |
|------|--------------|-------------|---------------|
| VS Code native | JSON (`mcp.json`) | `%APPDATA%\Code\User\mcp.json` | `"servers"."playwright-global"` |
| Cursor native | JSON (`mcp.json`) | `~\.cursor\mcp.json` | `"mcpServers"."playwright-global"` |
| Codex | TOML (`config.toml`) | `~\.codex\config.toml` | `[mcp_servers.playwright-global]` |
| Continue | YAML (`config.yaml`) | `~\.continue\config.yaml` | Top-level `mcpServers:` list |

## 4. Existing-State Inventory

| Host | Config Path | Scope | Server Name | Package | Args | Active? |
|------|------------|-------|-------------|---------|------|---------|
| VS Code workspace | `F:\Git\MCPtest\.vscode\mcp.json` | workspace | `playwright-local` | `@playwright/mcp@0.0.76` | `--user-data-dir ...\vscode-mcp-profile` | Yes |
| VS Code user | `%APPDATA%\Code\User\mcp.json` | user | *(no Playwright)* | — | — | N/A |
| Cursor user | `~\.cursor\mcp.json` | user | `playwright-local` | `@playwright/mcp@0.0.76` | `--user-data-dir ...\cursor-mcp-profile` | Yes |
| Codex user | `~\.codex\config.toml` | user | `playwright-local` | `@playwright/mcp@0.0.76` | `--user-data-dir ...\codex-mcp-profile` | Yes |
| Continue user | `~\.continue\config.yaml` | user | *(no Playwright)* | — | — | N/A |

**All existing entries use persistent profiles (`--user-data-dir`).** We will replace with `--isolated` for global availability.

## 5. Exact Proposed Changes

### Cursor (`~\.cursor\mcp.json`)
Replace entire `playwright-local` entry with `playwright-global` using `--isolated`.

### Codex (`~\.codex\config.toml`)
Rename `[mcp_servers.playwright-local]` → `[mcp_servers.playwright-global]`, switch args to `--isolated`.

### Continue (`~\.continue\config.yaml`)
Add top-level `mcpServers:` block before `slashCommands:`. No existing Playwright entry to replace.

### VS Code user (`%APPDATA%\Code\User\mcp.json`)
Add `playwright-global` entry to the existing `"servers"` object alongside 6 existing servers.

## 6. Duplicate-Resolution Strategy

1. Rename all workspace-level `playwright-local` → `playwright-global` user-level.
2. After each global host validates, remove workspace-level Playwright entry.
3. Do not remove unrelated workspace MCP servers (markitdown, netdata, etc.).
4. Continue has no workspace-level `.continue/mcpServers/` to clean up.

## 7. Backup Strategy

Timestamped backups stored in `~\.mcp-config-backups\<YYYYMMDD-HHMMSS>\`:
- `cursor-mcp.json`
- `codex-config.toml`
- `continue-config.yaml`
- `vscode-user-mcp.json`
- `backup-manifest.txt` (SHA-256 hashes)
- Never committed to Git

## 8. Configuration-Validation Strategy

- JSON: `ConvertFrom-Json`
- TOML: `python -c "import tomllib; tomllib.loads(...)"`
- YAML: Visual inspection + single `mcpServers:` key check
- Structural: Verify server appears in host's MCP panel

## 9. Functional-Validation Strategy

Clean smoke-test workspace (`F:\Git\MCPGlobalSmokeTest`) with no local configs.
Restricted test using only safe tools: `browser_navigate`, `browser_snapshot`, `browser_console_messages`, `browser_network_requests`, `browser_close`.

## 10. Security and Approval Policy

- Keep MCP tool approval prompts enabled
- Prefer dedicated safe tools over `browser_run_code_unsafe`
- Use `--isolated` to prevent cookie/profile sharing
- No personal Chrome profile reuse
- No secrets in Git

## 11. Rollback Procedure

```powershell
$bk = "C:\Users\cebit.ir\.mcp-config-backups\<TIMESTAMP>"
Copy-Item "$bk\cursor-mcp.json" "C:\Users\cebit.ir\.cursor\mcp.json"
Copy-Item "$bk\codex-config.toml" "C:\Users\cebit.ir\.codex\config.toml"
Copy-Item "$bk\continue-config.yaml" "C:\Users\cebit.ir\.continue\config.yaml"
Copy-Item "$bk\vscode-user-mcp.json" "$env:APPDATA\Code\User\mcp.json"
```

## 12. Evidence Paths

```
F:\Git\MCPtest\evidence\global\
├── pre-change-inventory.txt
├── backup-manifest-redacted.txt
├── cursor-global-validation.txt
├── codex-global-validation.txt
├── vscode-native-global-validation.txt
├── continue-vscode-global-validation.txt
├── continue-cursor-global-validation.txt
└── global-validation-matrix.md
```

## 13. Completion Criteria

All five hosts pass structural + functional validation from the clean smoke-test workspace.

## 14. Known Limitations

- Continue exposes MCP tools **only in Agent mode** with a tool-capable model.
- Cursor `--version` CLI flag is not supported.
- VS Code user-profile MCP is at `%APPDATA%\Code\User\mcp.json`.

## 15. Future Migration

Once the remote HTTP MCP server is deployed, all local STDIO entries can be replaced by one shared HTTP endpoint (`http://127.0.0.1:8931/mcp`), reducing the number of browser processes from 5 to 1.
