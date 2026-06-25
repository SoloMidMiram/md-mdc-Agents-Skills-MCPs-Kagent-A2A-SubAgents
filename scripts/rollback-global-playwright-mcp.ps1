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

# --- Parse manifest (hash entries + ABSENT_BEFORE_INSTALL tombstones) ---
$manifest = Join-Path $BackupDir "manifest-sha256.txt"
$absentBefore = @{}  # key: BackupName, tracks files created by installer
$expectedHashes = @{}  # key: BackupName, value: expected SHA-256
if (Test-Path $manifest) {
    Write-Output "--- Parsing manifest ---"
    foreach ($line in (Get-Content $manifest)) {
        if ($line -match '^ABSENT_BEFORE_INSTALL:(.+?) \| (.+)$') {
            $backupName = $matches[1]
            $absentBefore[$backupName] = $true
            Write-Output "[TOMBSTONE] ${backupName} was created by installer"
        } elseif ($line -match '^(.+?) \| ([A-F0-9]{64})') {
            $backupName = $matches[1]
            $expectedHashes[$backupName] = $matches[2]
        }
    }
} else {
    Write-Output "[INFO] No manifest found -- all backup files will be restored without hash validation"
}

# --- Build action plan from manifest entries + backup files ---
Write-Output "`nActions to perform:"
$rollbackPlan = @()  # each: @{Target = $t; Action = "restore|delete|skip|fail"; BackupFile = "..."; Reason = "..."}
foreach ($t in $Script:ConfigTargets) {
    $src = Join-Path $BackupDir $t.BackupName
    $dest = $t.Source
    $bn = $t.BackupName
    if ($absentBefore.ContainsKey($bn)) {
        $rollbackPlan += @{ Target = $t; Action = "delete"; BackupFile = $src; Reason = "file was created by installer" }
        Write-Output "  [DELETE] ${bn} -> $dest"
    } elseif (Test-Path $src) {
        $rollbackPlan += @{ Target = $t; Action = "restore"; BackupFile = $src; Reason = "backup exists" }
        Write-Output "  [RESTORE] ${bn} -> $dest"
    } elseif ($expectedHashes.ContainsKey($bn)) {
        $rollbackPlan += @{ Target = $t; Action = "fail"; Reason = "listed in manifest but backup file missing: ${bn}" }
        Write-Output "  [FAIL] ${bn} -- listed in manifest but backup file is missing"
    } else {
        $rollbackPlan += @{ Target = $t; Action = "skip"; Reason = "not in this backup set" }
        Write-Output "  [SKIP] ${bn} -- not affected by this backup"
    }
}

$restoreTargets = $rollbackPlan | Where-Object { $_.Action -in @("restore","delete") }
$failTargets = $rollbackPlan | Where-Object { $_.Action -eq "fail" }

if ($failTargets.Count -gt 0) {
    Write-Error "Backup validation failed: some files listed in manifest are missing."
    exit 1
}

if ($restoreTargets.Count -eq 0) {
    Write-Error "No backup or tombstone entries found in $BackupDir"
    exit 1
}

Write-Output ""
if (-not $Force) {
    if (Test-Path $manifest) {
        Write-Output "Backup manifest:"
        Get-Content $manifest
        Write-Output ""
    }
    $confirm = Read-Host "Process these $($restoreTargets.Count) actions? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Output "Rollback cancelled."
        exit 0
    }
}

# --- Validate backup hashes before restoring ---
if ($expectedHashes.Count -gt 0) {
    Write-Output "--- Validating backup hashes ---"
    $hashMismatch = $false
    foreach ($kv in $expectedHashes.GetEnumerator()) {
        $backupName = $kv.Key
        $expectedHash = $kv.Value
        $backupFile = Join-Path $BackupDir $backupName
        if (Test-Path $backupFile) {
            $actualHash = (Get-FileHash $backupFile -Algorithm SHA256).Hash
            if ($actualHash -ne $expectedHash) {
                Write-Output "[FAIL] Hash mismatch for ${backupName}: expected ${expectedHash}, got ${actualHash}"
                $hashMismatch = $true
            } else {
                Write-Output "[PASS] ${backupName} hash matches manifest"
            }
        } else {
            Write-Output "[FAIL] Backup listed in manifest is missing: ${backupName}"
            $hashMismatch = $true
        }
    }
    if ($hashMismatch) {
        Write-Error "Backup hash validation failed. Restore manually from the backup directory."
        exit 1
    }
}

# --- Apply all actions ---
foreach ($planItem in $rollbackPlan) {
    if ($planItem.Action -eq "delete") {
        $dest = $planItem.Target.Source
        if (Test-Path $dest) {
            Remove-Item $dest -Force -ErrorAction SilentlyContinue
            Write-Output "[DELETED] $($planItem.Target.BackupName) (created by installer, no original to restore)"
        }
    } elseif ($planItem.Action -eq "restore") {
        $src = $planItem.BackupFile
        $dest = $planItem.Target.Source
        Copy-Item $src $dest -Force
        Write-Output "[RESTORED] $($planItem.Target.BackupName) -> $dest"
    }
}

Write-Output ""
Write-Output "=== Rollback Complete ==="
Write-Output "Reload your editors to apply restored configurations."
Write-Output "Run .\verify-global-playwright-mcp.ps1 to validate."

