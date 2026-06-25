<#
.SYNOPSIS
    Verify playwright-global MCP configuration across all registered hosts.
    Exits with code 1 if any required check fails.
    Optional failures (warnings) are reported but do not cause exit.
#>

$ErrorActionPreference = "Continue"
$failures = @()
$warnings = @()

# Load shared config target manifest
. "$PSScriptRoot\McpConfigTargets.ps1"

function Add-Failure {
    param([string]$Message)
    $script:failures += $Message
    Write-Output "[FAIL] $Message"
}

function Add-Warning {
    param([string]$Message)
    $script:warnings += $Message
    Write-Output "[WARN] $Message"
}

Write-Output "=== playwright-global Verifier ==="
Write-Output ""

# --- Command Availability (optional = warning) ---
Write-Output "--- Command Availability ---"
$requiredCmds = @("node","npm","npx","python","codex")
$optionalCmds = @("code","cursor")
foreach ($cmd in $requiredCmds) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) { Write-Output "[PASS] $cmd -> $($found.Source)" }
    else        { Add-Failure "$cmd - not found (required)" }
}
foreach ($cmd in $optionalCmds) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) { Write-Output "[PASS] $cmd -> $($found.Source)" }
    else        { Add-Warning "$cmd - not found (optional)" }
}
Write-Output ""

# --- Package ---
Write-Output "--- Package ---"
try {
    $help = npx -y "$Package" --help 2>&1 | Select-String -Pattern "Usage:" -Quiet
    if ($help) { Write-Output "[PASS] $Package - available" }
    else       { Add-Failure "$Package - unexpected output" }
} catch {
    Add-Failure "$Package - error: $_"
}
Write-Output ""

# --- Host Configuration (4 config targets) ---
Write-Output "--- Host Configuration (4 config targets) ---"
foreach ($t in $Script:ConfigTargets) {
    $name = $t.Name
    if (-not (Test-Path $t.Source)) {
        Add-Failure "$name - file not found"
        continue
    }
    $actual = Get-ActualEntry $t
    if (-not $actual) {
        Add-Failure "$name - $ServerName entry not found"
        continue
    }
    if (Test-EntryMatches $actual $t) {
        $argsLine = $actual.args -join " "
        Write-Output "[PASS] $name - $ServerName correct [$argsLine]"
    } else {
        $detail = "command='$($actual.command)', args='$($actual.args -join ' ')'"
        if ($t.DesiredType) { $detail += ", type='$($actual.type)'" }
        Add-Failure "$name - $ServerName mismatch ($detail)"
    }
}
Write-Output ""

# --- Workspace Duplicates ---
Write-Output "--- Workspace Duplicates ---"
$repoRoot = Split-Path -Parent $PSScriptRoot
$wf1 = Join-Path $repoRoot ".vscode\mcp.json"
if (Test-Path $wf1) {
    $wc = Get-Content $wf1 -Raw
    if ($wc -match "playwright") { Add-Warning "$wf1 - still has playwright entry" }
    else { Write-Output "[PASS] $wf1 - clean" }
}
$wf2 = Join-Path $repoRoot ".continue\mcpServers"
if (Test-Path $wf2) { Add-Warning "$wf2 - exists (should be removed)" }
else { Write-Output "[PASS] $wf2 - absent" }
$wf3 = Join-Path $repoRoot ".codex\config.toml"
if (Test-Path $wf3) { Add-Warning "$wf3 - exists (should be removed)" }
else { Write-Output "[PASS] $wf3 - absent" }

Write-Output ""
Write-Output "=== Summary ==="
Write-Output "Configuration targets: 4"
Write-Output "Runtime surfaces: 5 (VS Code, Cursor, Codex, Continue in VS Code, Continue in Cursor)"
if ($warnings.Count -gt 0) {
    Write-Output "Warnings: $($warnings.Count)"
    $warnings | ForEach-Object { Write-Output "  - $_" }
}
if ($failures.Count -gt 0) {
    Write-Output "Failures: $($failures.Count)"
    $failures | ForEach-Object { Write-Output "  - $_" }
    Write-Output "`n=== VERIFICATION FAILED ==="
    exit 1
} else {
    Write-Output "All required checks passed."
    Write-Output "`n=== VERIFICATION PASSED ==="
    exit 0
}
