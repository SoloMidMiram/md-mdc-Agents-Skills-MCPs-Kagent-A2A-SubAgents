# Runbook: AI Tooling Integration

## Purpose
Document how to operate and maintain the controlled integration scaffold for
Playwright MCP, Azure tooling, and Foundry Toolkit.

## Quick Reference

### Playwright MCP
```
Server:          playwright-global
Package:         @playwright/mcp@0.0.76
Transport:       STDIO
Flags:           --isolated
Available in:    VS Code, Cursor, Codex, Continue
```

### Azure Resources (VS Code only)
```
Extension:  ms-azuretools.vscode-azureresourcegroups
Version:    0.12.7
State:      INSTALLED_DORMANT
```

### Azure MCP Server (VS Code only)
```
Extension:  ms-azuretools.vscode-azure-mcp-server
Version:    2.0.45
State:      INSTALLED_DORMANT
Policy:     READ_ONLY_POLICY_PREPARED
Started:    NO
```

### Foundry Toolkit (VS Code only)
```
Extension:  ms-windows-ai-studio.windows-ai-studio
Version:    1.6.1
State:      INSTALLED_LOCAL_ONLY
```

### Chat Customizations Evaluations
```
Extension:  ms-vscode.vscode-chat-customizations-evaluations
Version:    1.0.7
State:      PLACEHOLDER_UNVERIFIED
```

## Rollback

```powershell
# Remove extensions installed by this task (only if they didn't exist before)
code --uninstall-extension ms-azuretools.vscode-azureresourcegroups
code --uninstall-extension ms-azuretools.vscode-azure-mcp-server
code --uninstall-extension ms-windows-ai-studio.windows-ai-studio

# Restore from backup
$bk = "C:\Users\cebit.ir\.mcp-config-backups\<TIMESTAMP>"
Copy-Item "$bk\vscode-user-mcp.json" "$env:APPDATA\Code\User\mcp.json" -Force
Copy-Item "$bk\vscode-user-settings.json" "$env:APPDATA\Code\User\settings.json" -Force
```
