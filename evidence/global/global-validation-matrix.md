# Global Playwright MCP Validation Matrix

Date: 2026-06-24

## Configuration Targets: 4 / Runtime Surfaces: 5

| # | Runtime Surface | Editor | Config Target | Server Name | Structural | Discovery | Functional |
|---|----------------|--------|--------------|-------------|------------|-----------|------------|
| 1 | Codex CLI | Codex CLI | Codex (`config.toml`) | `playwright-global` | STRUCTURAL_PASS | DISCOVERY_PASS | PENDING |
| 2 | VS Code native Copilot | VS Code | VS Code (`mcp.json`) | `playwright-global` | STRUCTURAL_PASS | PENDING | PENDING |
| 3 | Cursor native agent | Cursor | Cursor (`mcp.json`) | `playwright-global` | STRUCTURAL_PASS | PENDING | PENDING |
| 4 | Continue in VS Code | VS Code | Continue (`config.yaml`) | `playwright-global` | STRUCTURAL_PASS | PENDING | PENDING |
| 5 | Continue in Cursor | Cursor | Continue (`config.yaml`) | `playwright-global` | STRUCTURAL_PASS | PENDING | PENDING |

### Status Level Definitions

| Level | Meaning |
|-------|---------|
| NOT_CONFIGURED | No usable registration |
| STRUCTURAL_PASS | Config parses and expected fields exist |
| DISCOVERY_PASS | Host lists or discovers the MCP server |
| FUNCTIONAL_PASS | A real MCP tool invocation succeeded |

**Note:** Codex achieves DISCOVERY_PASS because `codex mcp list` confirms the
server is registered and enabled. The other 4 surfaces require interactive
editor sessions to confirm discovery and functional operation.

## Structural Verification — All PASS

| Check | Cursor | Codex | Continue | VS Code |
|-------|--------|-------|----------|---------|
| Syntax valid | JSON | TOML | YAML (single `mcpServers:`) | JSON |
| Server name | `playwright-global` | `playwright-global` | `playwright-global` | `playwright-global` |
| Package | `@playwright/mcp@0.0.76` | `@playwright/mcp@0.0.76` | `@playwright/mcp@0.0.76` | `@playwright/mcp@0.0.76` |
| `--isolated` | Yes | Yes | Yes | Yes |
| Existing config preserved | N/A (sole entry) | `[projects.*]`, `[windows]` | 10+ models, rules, slashCommands | 6 servers + inputs |

## Workspace Cleanliness

- `F:\Git\MCPGlobalSmokeTest` — clean (no MCP config files)
- `F:\Git\MCPtest\.vscode\mcp.json` — empty `"servers": {}` (workspace duplicate removed)
- `F:\Git\MCPtest\.continue\mcpServers\` — absent
- `F:\Git\MCPtest\.codex\config.toml` — absent

## Duplicate Resolution

| Removed Entry | Original Location | Disposition |
|--------------|-------------------|-------------|
| `playwright-local` (VS Code workspace) | `F:\Git\MCPtest\.vscode\mcp.json` | Archived to `docs/templates/mcp-vscode-workspace.json` |
| `playwright-local` (Cursor user) | `~\.cursor\mcp.json` | Renamed to `playwright-global` |
| `playwright-local` (Codex user) | `~\.codex\config.toml` | Renamed to `playwright-global` |

## Functional Validation Status

**Verdict:** GLOBAL_PLAYWRIGHT_MCP_CONFIGURED_PENDING_VALIDATION

All 5 hosts are structurally configured and verified. Full functional
validation (browser_navigate, browser_snapshot, browser_console_messages,
browser_network_requests, browser_close) requires opening the clean
smoke-test workspace (F:\Git\MCPGlobalSmokeTest) in each editor and running
the restricted example.com test interactively.

### How to validate each host

1. **Codex:** In the smoke-test workspace, start `codex` and run the restricted test.
2. **VS Code native:** Open `F:\Git\MCPGlobalSmokeTest`, Copilot Chat → Agent mode → run test.
3. **Cursor native:** Open `F:\Git\MCPGlobalSmokeTest`, Cursor Agent → run test.
4. **Continue in VS Code:** Open `F:\Git\MCPGlobalSmokeTest`, Continue panel → Agent mode → run test.
5. **Continue in Cursor:** Open `F:\Git\MCPGlobalSmokeTest`, Continue panel → Agent mode → run test.
