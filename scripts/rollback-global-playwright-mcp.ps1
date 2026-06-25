<#
.SYNOPSIS
    Roll back playwright-global MCP configuration changes from a specific backup.
.DESCRIPTION
    Restores all user-level MCP configs from a named backup directory.
    Uses the same backup filenames as the installer for round-trip compatibility.
    Requires an explicit backup path. Shows files to restore before proceeding.
    Use -Force to skip confirmation prompt.
.PARAMETER BackupDir
    The backup directory path (e.g., $env:USERPROFILE\.mcp-config-backups\20260624-085526)
.PARAMETER Force
    Skip confirmation prompt.
.PARAMETER ConfigRoot
    Override config root for testing. If provided, all config file paths are rebased
    to this directory instead of the real user profile.
.EXAMPLE
    .\rollback-global-playwright-mcp.ps1 -BackupDir "$env:USERPROFILE\.mcp-config-backups\20260624-085526"
.EXAMPLE
    .\rollback-global-playwright-mcp.ps1 -BackupDir "$env:USERPROFILE\.mcp-config-backups\20260624-085526" -Force
.EXAMPLE
    .\rollback-global-playwright-mcp.ps1 -BackupDir C:\Backups\20260624-085526 -ConfigRoot C:\Temp\TestWorkspace
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir,
    [switch]$Force,
    [string]$ConfigRoot = $null
)

$ErrorActionPreference = "Stop"

# Load shared config target manifest
. "$PSScriptRoot\McpConfigTargets.ps1"

# If ConfigRoot is provided, rebase all target paths for testability
if ($ConfigRoot) {
    $cr = $ConfigRoot.TrimEnd('\')
    $up = $env:USERPROFILE.TrimEnd('\')
    $ad = $env:APPDATA.TrimEnd('\')
    foreach ($t in $Script:ConfigTargets) {
        $t.Source = $t.Source -replace [regex]::Escape($up), $cr
        $t.Source = $t.Source -replace [regex]::Escape($ad), (Join-Path $cr "AppData\Roaming")
    }
    $Script:BackupRoot = Join-Path $cr ".mcp-config-backups"
}

if (-not (Test-Path $BackupDir)) {
    Write-Error "Backup directory not found: $BackupDir"
    exit 1
}

Write-Output "=== Rollback: playwright-global MCP ==="
Write-Output "Backup directory: $BackupDir"
Write-Output ""

Write-Output "Files to restore:"
$availableFiles = @()
foreach ($t in $Script:ConfigTargets) {
    $src = Join-Path $BackupDir $t.BackupName
    $dest = $t.Source
    if (Test-Path $src) {
        Write-Output "  $($t.BackupName) -> $dest"
        $availableFiles += $t
    } else {
        Write-Output "  $($t.BackupName) - NOT IN BACKUP (skipping)"
    }
}

if ($availableFiles.Count -eq 0) {
    Write-Error "No backup files found in $BackupDir"
    exit 1
}

Write-Output ""
if (-not $Force) {
    $manifest = Join-Path $BackupDir "manifest-sha256.txt"
    if (Test-Path $manifest) {
        Write-Output "Backup manifest:"
        Get-Content $manifest
        Write-Output ""
    }
    $confirm = Read-Host "Restore these $($availableFiles.Count) file(s)? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Output "Rollback cancelled."
        exit 0
    }
}

foreach ($t in $availableFiles) {
    $src = Join-Path $BackupDir $t.BackupName
    $dest = $t.Source
    Copy-Item $src $dest -Force
    Write-Output "[RESTORED] $($t.BackupName) -> $dest"
}

Write-Output ""
Write-Output "=== Rollback Complete ==="
Write-Output "Reload your editors to apply restored configurations."
Write-Output "Run .\verify-global-playwright-mcp.ps1 to validate."
