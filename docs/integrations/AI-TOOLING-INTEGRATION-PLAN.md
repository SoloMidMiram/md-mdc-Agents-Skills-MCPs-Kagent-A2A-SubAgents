# AI Tooling Integration Plan

## Objective
Controlled integration scaffold for Playwright MCP, Azure tooling, Foundry Toolkit,
and Chat Customizations Evaluations in the MCPtest laboratory workspace.

## Architectural Layers

| Layer | Components | State |
|-------|-----------|-------|
| Local browser automation | Playwright MCP (playwright-global) | PRESERVED_ACTIVE |
| Local tooling | Foundry Toolkit, Chat Customizations Evaluations | LOCAL_ONLY |
| Azure resource browsing | Azure Resources for VS Code | INSTALLED_DORMANT |
| Azure MCP server | Azure MCP Server for VS Code | INSTALLED_DORMANT |
| Cursor bridge (future) | Azure MCP for Cursor | DOCUMENTATION_PLACEHOLDER_ONLY |

## Supported Hosts

- VS Code native Copilot (Playwright, Azure MCP, Foundry)
- Cursor native agent (Playwright only; Azure/Foundry deferred)
- Codex CLI (Playwright only)
- Continue in VS Code (Playwright only)

## Non-Goals

- No Azure resource creation
- No model or agent deployment
- No metered model runs
- No cloud costs
- No Azure sign-in/sign-out
- No Azure MCP startup
- No live Cursor MCP config changes for Azure
- No secrets in repository

## Activation Gates

See docs/integrations/ACTIVATION-GATES.md for full gate matrix.
