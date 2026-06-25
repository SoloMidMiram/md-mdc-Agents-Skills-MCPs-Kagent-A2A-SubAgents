# Global Playwright MCP Implementation

## 1. Final Architecture

Five independent user-level MCP registrations for the `playwright-global` server:

```
VS Code native (user mcp.json)
    → npx -y @playwright/mcp@0.0.76 --isolated
Cursor native (user mcp.json)
    → npx -y @playwright/mcp@0.0.76 --isolated
Codex (user config.toml)
    → npx -y @playwright/mcp@0.0.76 --isolated
Continue (user config.yaml)
    → npx -y @playwright/mcp@0.0.76 --isolated
```

No cross-IDE registry exists. Each host independently reads its own config.

## 2. Supported Hosts

| Host | Mode Required |
|------|--------------|
| VS Code native Copilot agent | Any agent mode |
| Cursor native agent | Any agent mode |
| Codex CLI | `codex chat` or `codex` |
| Continue in VS Code | Agent mode only |
| Continue in Cursor | Agent mode only |

## 3. User-Level Paths

| Host | Config Path |
|------|------------|
| VS Code | `%APPDATA%\Code\User\mcp.json` |
| Cursor | `C:\Users\cebit.ir\.cursor\mcp.json` |
| Codex | `C:\Users\cebit.ir\.codex\config.toml` |
| Continue | `C:\Users\cebit.ir\.continue\config.yaml` |

## 4. Before-and-After Configuration Excerpts

### Cursor (`~\.cursor\mcp.json`)
**Before:**
```json
"playwright-local": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@0.0.76", "--user-data-dir", "..."]
}
```
**After:**
```json
"playwright-global": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@0.0.76", "--isolated"]
}
```

### Codex (`~\.codex\config.toml`)
**Before:**
```toml
[mcp_servers.playwright-local]
command = "npx"
args = ["-y", "@playwright/mcp@0.0.76", "--user-data-dir", '...']
```
**After:**
```toml
[mcp_servers.playwright-global]
command = "npx"
args = ["-y", "@playwright/mcp@0.0.76", "--isolated"]
```

### Continue (`~\.continue\config.yaml`)
**Before:** (no mcpServers section)
**After:**
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

### VS Code user (`%APPDATA%\Code\User\mcp.json`)
**Before:** (6 existing servers, no Playwright)
**After:** Added to `"servers"`:
```json
"playwright-global": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@playwright/mcp@0.0.76", "--isolated"]
}
```

## 5. Backup Location

```
C:\Users\cebit.ir\.mcp-config-backups\20260624-085526\
├── cursor-mcp.json
├── codex-config.toml
├── continue-config.yaml
├── vscode-user-mcp.json
└── backup-manifest.txt
```

## 6. Hash Manifest

See `evidence/global/backup-manifest-redacted.txt` (full hashes in backup dir).

## 7. Commands Executed

```powershell
# Phase 1: Environment inspection
node --version; npm --version; npx --version
code --version; cursor --version; codex --version
npx -y "@playwright/mcp@0.0.76" --help

# Phase 4: Backups
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$bk = "C:\Users\cebit.ir\.mcp-config-backups\$ts"
New-Item -ItemType Directory -Path $bk -Force
Copy-Item "C:\Users\cebit.ir\.cursor\mcp.json" "$bk\cursor-mcp.json"
Copy-Item "C:\Users\cebit.ir\.codex\config.toml" "$bk\codex-config.toml"
Copy-Item "C:\Users\cebit.ir\.continue\config.yaml" "$bk\continue-config.yaml"
Copy-Item "$env:APPDATA\Code\User\mcp.json" "$bk\vscode-user-mcp.json"
Get-FileHash "$bk\*" -Algorithm SHA256 | Format-Table

# Phase 5: Cursor - rename & switch to --isolated
# (file edit via replace_string_in_file)

# Phase 6: Codex - rename & switch to --isolated
# (file edit via replace_string_in_file)

# Phase 7: Continue - add mcpServers block
# (file edit via replace_string_in_file)

# Phase 8: VS Code user - add playwright-global
# (file edit via replace_string_in_file)

# Phase 9: Workspace duplicate resolution
# Refreshed docs/templates/mcp-vscode-workspace.json as an empty workspace template
# Cleared .vscode/mcp.json servers object

# Phase 10: Smoke-test workspace
New-Item -ItemType Directory -Path "F:\Git\MCPGlobalSmokeTest" -Force
```

## 8. Structural Validation Results

| Host | Validation | Result |
|------|-----------|--------|
| Cursor JSON | `ConvertFrom-Json` | PASS |
| Codex TOML | `tomllib.loads` | PASS (TOML_OK) |
| Continue YAML | Single `mcpServers:` check | PASS |
| VS Code user JSON | `ConvertFrom-Json` | PASS |
| Codex CLI | `codex mcp list` | PASS (playwright-global visible) |

## 9. Functional Validation Matrix

| Host | Workspace | Status |
|------|-----------|--------|
| Codex from smoke-test | F:\Git\MCPGlobalSmokeTest | PENDING_INTERACTIVE_VALIDATION |
| VS Code native from smoke-test | F:\Git\MCPGlobalSmokeTest | PENDING_INTERACTIVE_VALIDATION |
| Cursor native from smoke-test | F:\Git\MCPGlobalSmokeTest | PENDING_INTERACTIVE_VALIDATION |
| Continue in VS Code | F:\Git\MCPGlobalSmokeTest | PENDING_INTERACTIVE_VALIDATION |
| Continue in Cursor | F:\Git\MCPGlobalSmokeTest | PENDING_INTERACTIVE_VALIDATION |

## 10. Duplicate Workspace Configurations Removed

- `F:\Git\MCPtest\.vscode\mcp.json`: `playwright-local` removed (now empty servers object). `docs/templates/mcp-vscode-workspace.json` is now the empty workspace template.
- `F:\Git\MCPtest\.continue\mcpServers\`: Did not exist — nothing to remove.
- `F:\Git\MCPtest\.codex\config.toml`: Did not exist — nothing to remove.
- Cursor workspace: No workspace-level config exists.

## 11. Remaining Limitations

- Continue exposes MCP only in Agent mode with a tool-capable model.
- All 4 config targets run separate browser processes (5 Chromium instances across 5 runtime surfaces when used simultaneously).
- Browser state is not shared between hosts (`--isolated`).

## 12. Agent-Mode Requirements

| Host | Agent Mode? |
|------|-------------|
| VS Code Copilot | Agent mode only for MCP tool access |
| Cursor | Agent mode for MCP tool access |
| Continue | Agent mode required — Chat/Edit/Autocomplete cannot use MCP |

## 13. Approval and Safety Policy

- MCP tool approval prompts remain enabled by default.
- Safe dedicated tools (`browser_navigate`, `browser_snapshot`, etc.) preferred.
- `browser_run_code_unsafe` restricted where configurable.
- No personal Chrome profile used.

## 14. Rollback Commands

```powershell
$bk = "C:\Users\cebit.ir\.mcp-config-backups\20260624-085526"
Copy-Item "$bk\cursor-mcp.json" "C:\Users\cebit.ir\.cursor\mcp.json" -Force
Copy-Item "$bk\codex-config.toml" "C:\Users\cebit.ir\.codex\config.toml" -Force
Copy-Item "$bk\continue-config.yaml" "C:\Users\cebit.ir\.continue\config.yaml" -Force
Copy-Item "$bk\vscode-user-mcp.json" "$env:APPDATA\Code\User\mcp.json" -Force
# Restore workspace .vscode/mcp.json from docs/templates/mcp-vscode-workspace.json
# The workspace template is intentionally empty; user-level configs provide Playwright.
```

## 15. How to Add Another MCP Host Later

1. Locate that host's user-level MCP configuration file.
2. Add a `playwright-global` entry with the same `npx -y @playwright/mcp@0.0.76 --isolated` command.
3. Create a timestamped backup first.
4. Validate the config syntax.
5. Test from a clean workspace.

## 16. Future Conversion to Shared HTTP MCP

Once the remote HTTP MCP server is deployed (`127.0.0.1:8931/mcp` over SSH tunnel),
all 5 STDIO entries can be replaced by one shared endpoint, reducing
browser processes from 5 to 1.
