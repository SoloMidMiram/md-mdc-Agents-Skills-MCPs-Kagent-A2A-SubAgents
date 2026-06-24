<#
.SYNOPSIS
    Inventory all AI tooling extensions and MCP configurations for the scaffold.
.DESCRIPTION
    Reads and reports the current state of all tooling components.
    Never modifies any configuration.
#>

$ErrorActionPreference = "Continue"

Write-Output "=== AI Tooling Inventory ==="
Write-Output "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Output ""

# 1. VS Code version
Write-Output "--- VS Code ---"
code --version 2>&1 | Select-Object -First 1

# 2. Key extensions
Write-Output "`n--- Key Extensions (VS Code) ---"
$targets = @(
    "ms-azuretools.vscode-azureresourcegroups",
    "ms-azuretools.vscode-azure-mcp-server",
    "ms-windows-ai-studio.windows-ai-studio",
    "ms-vscode.vscode-chat-customizations-evaluations",
    "continue.continue"
)
$allExts = code --list-extensions --show-versions 2>&1
foreach ($t in $targets) {
    $line = $allExts | Select-String -Pattern $t -SimpleMatch -Quiet
    if ($line) {
        $version = ($allExts | Select-String -Pattern "$t@" -SimpleMatch).ToString()
        Write-Output "[FOUND] $version"
    } else {
        Write-Output "[MISSING] $t"
    }
}

# 3. Playwright MCP registrations
Write-Output "`n--- Playwright MCP Registrations ---"
$playwrightFiles = @(
    "$env:APPDATA\Code\User\mcp.json",
    "$env:USERPROFILE\.cursor\mcp.json",
    "$env:USERPROFILE\.codex\config.toml",
    "$env:USERPROFILE\.continue\config.yaml"
)
foreach ($pf in $playwrightFiles) {
    if (Test-Path $pf) {
        $content = Get-Content $pf -Raw
        if ($content -match "playwright-global|playwright-local|@playwright/mcp") {
            Write-Output "[ACTIVE] $pf"
        } else {
            Write-Output "[NO PLAYWRIGHT] $pf"
        }
    } else {
        Write-Output "[NOT FOUND] $pf"
    }
}

# 4. Azure MCP running status
Write-Output "`n--- Azure MCP Status ---"
$procs = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "azure-mcp" -or $_.CommandLine -match "mcp-server" }
if ($procs) {
    Write-Output "[RUNNING] Azure MCP process detected"
} else {
    Write-Output "[NOT RUNNING] Azure MCP process not detected"
}

# 5. Azure auth status
Write-Output "`n--- Azure Auth Status ---"
$az = Get-Command az -ErrorAction SilentlyContinue
if ($az) {
    Write-Output "[AZ CLI FOUND] $($az.Source)"
} else {
    Write-Output "[AZ CLI NOT INSTALLED]"
}

Write-Output "`n=== Inventory Complete ==="
