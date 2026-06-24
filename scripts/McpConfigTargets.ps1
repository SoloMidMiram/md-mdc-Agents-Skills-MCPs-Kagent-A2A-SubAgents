<#
.SYNOPSIS
    Shared MCP configuration target manifest for installer, rollback, and verifier.
.DESCRIPTION
    Single source of truth for MCP host configurations.
    Consumed by install-global-playwright-mcp.ps1, rollback-global-playwright-mcp.ps1,
    and verify-global-playwright-mcp.ps1 to ensure round-trip compatibility.
#>

$Script:ServerName = "playwright-global"
$Script:Package = "@playwright/mcp@0.0.76"
$Script:DesiredArgs = @("-y", $Script:Package, "--isolated")

$Script:ConfigTargets = @(
    @{
        Name       = "Cursor"
        Source     = Join-Path $env:USERPROFILE ".cursor\mcp.json"
        BackupName = "cursor-mcp.json"
        Format     = "JSON"
        ServerKey  = "mcpServers"
        TypeKey    = $null
        Desired    = @{ command = "npx"; args = $Script:DesiredArgs }
    }
    @{
        Name       = "Codex"
        Source     = Join-Path $env:USERPROFILE ".codex\config.toml"
        BackupName = "codex-config.toml"
        Format     = "TOML"
        ServerKey  = $null
        TypeKey    = $null
        Desired    = $null
    }
    @{
        Name       = "Continue"
        Source     = Join-Path $env:USERPROFILE ".continue\config.yaml"
        BackupName = "continue-config.yaml"
        Format     = "YAML"
        ServerKey  = $null
        TypeKey    = $null
        Desired    = $null
    }
    @{
        Name       = "VS Code"
        Source     = Join-Path $env:APPDATA "Code\User\mcp.json"
        BackupName = "vscode-user-mcp.json"
        Format     = "JSON"
        ServerKey  = "servers"
        TypeKey    = "stdio"
        Desired    = @{ type = "stdio"; command = "npx"; args = $Script:DesiredArgs }
    }
)

$Script:BackupRoot = Join-Path $env:USERPROFILE ".mcp-config-backups"

function New-BackupDir {
    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    $dir = Join-Path $Script:BackupRoot $ts
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    return $dir
}

function Backup-ConfigTargets {
    param([string]$BackupDir, [switch]$WhatIf)
    foreach ($t in $Script:ConfigTargets) {
        $dest = Join-Path $BackupDir $t.BackupName
        if (Test-Path $t.Source) {
            if (-not $WhatIf) {
                Copy-Item $t.Source $dest -Force
                $hash = (Get-FileHash $t.Source -Algorithm SHA256).Hash
                "$($t.BackupName) | $hash | $($t.Source)" | Out-File (Join-Path $BackupDir "manifest-sha256.txt") -Append -Encoding UTF8
            }
            Write-Output "[BACKUP] $($t.Name) -> $dest"
        } else {
            Write-Output "[SKIP] $($t.Name) - file not found at $($t.Source)"
        }
    }
}

function Get-ExpectedEntry {
    param($Target)
    if ($Target.Format -ne "JSON") { return $null }
    return $Target.Desired
}

function Test-EntryMatches {
    param($Actual, $Expected)
    if (-not $Actual) { return $false }
    if ($Actual.command -ne $Expected.command) { return $false }
    $aArgs = $Actual.args -join " "
    $eArgs = $Expected.args -join " "
    if ($aArgs -ne $eArgs) { return $false }
    if ($Expected.type -and $Actual.type -ne $Expected.type) { return $false }
    return $true
}
