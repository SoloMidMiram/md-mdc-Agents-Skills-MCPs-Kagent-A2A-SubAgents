# Host Capability Matrix

Date: 2026-06-24

## Current State

| Capability | VS Code Native | Cursor Native | Codex CLI | Continue (VS Code) |
|-----------|---------------|--------------|-----------|-------------------|
| Playwright MCP (browser) | ✅ ACTIVE | ✅ ACTIVE | ✅ ACTIVE | ✅ ACTIVE |
| Azure Resources browsing | ✅ INSTALLED_DORMANT | ❌ NOT INSTALLED | ❌ NOT INSTALLED | ❌ NOT INSTALLED |
| Azure MCP server | ✅ INSTALLED_DORMANT | ❌ CURSOR_PLACEHOLDER_DOCUMENTED | ❌ NOT INSTALLED | ❌ NOT INSTALLED |
| Foundry Toolkit | ✅ INSTALLED_LOCAL_ONLY | ❌ VSCODE_ONLY_UNTIL_VERIFIED | ❌ NOT INSTALLED | ❌ NOT INSTALLED |
| Chat Customizations Evaluations | ✅ INSTALLED_UNVERIFIED | ❌ COMPATIBILITY_PENDING | ❌ NOT INSTALLED | ❌ NOT INSTALLED |

## Notes

- Cursor does not support VS Code UI extensions (Azure Resources, Azure MCP, Foundry).
- Continue inherits Playwright from its own config.yaml, not from VS Code's mcp.json.
- Codex has its own independent Playwright registration.
- Azure MCP and Foundry are VS Code-specific unless documented otherwise.
