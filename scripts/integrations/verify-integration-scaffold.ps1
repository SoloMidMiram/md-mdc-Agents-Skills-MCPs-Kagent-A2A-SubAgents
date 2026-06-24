<#
.SYNOPSIS
    Verify the AI tooling integration scaffold after implementation.
.DESCRIPTION
    Validates that all scaffold files exist, JSON/YAML parse correctly,
    no secrets were introduced, and Playwright is preserved.
#>

$ErrorActionPreference = "Continue"
$root = "F:\Git\MCPtest"

Write-Output "=== Integration Scaffold Verification ==="
Write-Output ""

# 1. File existence
Write-Output "--- Required Files ---"
$required = @(
    "docs\integrations\AI-TOOLING-INTEGRATION-PLAN.md",
    "docs\integrations\HOST-CAPABILITY-MATRIX.md",
    "docs\integrations\ACTIVATION-GATES.md",
    "docs\integrations\RUNBOOK.md",
    "config\integrations\tooling-registry.yaml",
    "config\integrations\azure-mcp.placeholder.yaml",
    "config\integrations\foundry-cloud.placeholder.yaml",
    "scripts\integrations\inventory-tooling.ps1",
    ".gitignore"
)
$allExist = $true
foreach ($rf in $required) {
    $path = Join-Path $root $rf
    if (Test-Path $path) {
        Write-Output "[EXISTS] $rf"
    } else {
        Write-Output "[MISSING] $rf"
        $allExist = $false
    }
}

# 2. JSON check
Write-Output "`n--- JSON Validation ---"
$jsonFiles = @(
    "$env:APPDATA\Code\User\mcp.json",
    "$env:USERPROFILE\.cursor\mcp.json"
)
foreach ($jf in $jsonFiles) {
    if (Test-Path $jf) {
        try {
            $null = Get-Content $jf -Raw | ConvertFrom-Json
            Write-Output "[VALID JSON] $jf"
        } catch {
            Write-Output "[INVALID JSON] $jf : $_"
        }
    }
}

# 3. Playwright preserved check
Write-Output "`n--- Playwright Preservation ---"
$playwrightFiles = @(
    "$env:APPDATA\Code\User\mcp.json",
    "$env:USERPROFILE\.cursor\mcp.json",
    "$env:USERPROFILE\.codex\config.toml",
    "$env:USERPROFILE\.continue\config.yaml"
)
$pwOk = $true
foreach ($pf in $playwrightFiles) {
    if (Test-Path $pf) {
        $content = Get-Content $pf -Raw
        if ($content -match "playwright-global") {
            Write-Output "[PRESERVED] playwright-global in $pf"
        } elseif ($content -match "playwright") {
            Write-Output "[WARN] playwright entry not named playwright-global in $pf"
        } else {
            Write-Output "[MISSING] No playwright entry in $pf"
            $pwOk = $false
        }
    }
}

# 4. Secret scan (staged text only)
Write-Output "`n--- Secret Scan (staged files) ---"
$secrets = @("tenant.*id", "subscription.*id", "AZURE_SUBSCRIPTION", "AZURE_TENANT", "api_key:\s", "apiKey:\s")
$staged = git -C $root diff --cached --name-only 2>$null
foreach ($sf in $staged) {
    $sp = Join-Path $root $sf
    if (Test-Path $sp -PathType Leaf) {
        $content = Get-Content $sp -Raw
        foreach ($s in $secrets) {
            if ($content -match $s) {
                Write-Output "[WARN] Possible secret pattern '$s' in $sf"
            }
        }
    }
}
Write-Output "[SCAN COMPLETE] Staged text scanned for secret patterns"

# 5. Azure MCP not running
Write-Output "`n--- Azure MCP Running Check ---"
$procs = Get-Process -Name "node" -ErrorAction SilentlyContinue
$mcpProc = $false
foreach ($p in $procs) {
    try { if ($p.CommandLine -match "azure-mcp") { $mcpProc = $true } } catch {}
}
if ($mcpProc) { Write-Output "[WARN] Azure MCP process detected" }
else { Write-Output "[PASS] Azure MCP not running" }

Write-Output "`n=== Verification Complete ==="
