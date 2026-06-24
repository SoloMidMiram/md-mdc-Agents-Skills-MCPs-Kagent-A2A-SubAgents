<#
.SYNOPSIS
    Roll back playwright-global MCP configuration changes from a specific backup.
.DESCRIPTION
    Restores all user-level MCP configs from a named backup directory.
    Requires an explicit backup path. Shows files to restore before proceeding.
    Use -Force to skip confirmation prompt.
.PARAMETER BackupDir
    The backup directory path (e.g., C:\Users\cebit.ir\.mcp-config-backups\20260624-085526)
.PARAMETER Force
    Skip confirmation prompt.
.EXAMPLE
    .\rollback-global-playwright-mcp.ps1 -BackupDir "C:\Users\cebit.ir\.mcp-config-backups\20260624-085526"
.EXAMPLE
    .\rollback-global-playwright-mcp.ps1 -BackupDir "C:\Users\cebit.ir\.mcp-config-backups\20260624-085526" -Force
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
    Write-Error "Backup directory not found: $BackupDir"
    exit 1
}

$restoreMap = @{
    "cursor-mcp.json"       = "C:\Users\cebit.ir\.cursor\mcp.json"
    "codex-config.toml"     = "C:\Users\cebit.ir\.codex\config.toml"
    "continue-config.yaml"  = "C:\Users\cebit.ir\.continue\config.yaml"
    "vscode-user-mcp.json"  = "$env:APPDATA\Code\User\mcp.json"
}

Write-Output "=== Rollback: playwright-global MCP ==="
Write-Output "Backup directory: $BackupDir"
Write-Output ""

Write-Output "Files to restore:"
$availableFiles = @()
foreach ($entry in $restoreMap.Keys) {
    $src = Join-Path $BackupDir $entry
    $dest = $restoreMap[$entry]
    if (Test-Path $src) {
        Write-Output "  $entry → $dest"
        $availableFiles += $entry
    } else {
        Write-Output "  $entry — NOT IN BACKUP (skipping)"
    }
}

if ($availableFiles.Count -eq 0) {
    Write-Error "No backup files found in $BackupDir"
    exit 1
}

Write-Output ""
if (-not $Force) {
    Write-Output "Backup manifest:"
    $manifest = Join-Path $BackupDir "backup-manifest.txt"
    if (Test-Path $manifest) { Get-Content $manifest }
    else { Write-Output "(no manifest file)" }
    Write-Output ""
    $confirm = Read-Host "Restore these $($availableFiles.Count) file(s)? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Output "Rollback cancelled."
        exit 0
    }
}

foreach ($entry in $availableFiles) {
    $src = Join-Path $BackupDir $entry
    $dest = $restoreMap[$entry]
    Copy-Item $src $dest -Force
    Write-Output "[RESTORED] $entry → $dest"
}

Write-Output ""
Write-Output "=== Rollback Complete ==="
Write-Output "Reload your editors to apply restored configurations."
Write-Output "Run .\verify-global-playwright-mcp.ps1 to validate."
