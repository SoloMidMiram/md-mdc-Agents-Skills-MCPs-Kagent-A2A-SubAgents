<#
.SYNOPSIS
    Verify playwright-global MCP configuration across all registered hosts.
    Exits with code 1 if any check fails.
#>

$ErrorActionPreference = "Continue"
$failures = @()

# Load shared config target manifest
. "$PSScriptRoot\McpConfigTargets.ps1"

function Add-Failure {
    param([string]$Message)
    $script:failures += $Message
    Write-Output "[FAIL] $Message"
}

Write-Output "=== playwright-global Verifier ==="
Write-Output ""

# --- Command Availability ---
Write-Output "--- Command Availability ---"
foreach ($cmd in @("node","npm","npx","code","cursor","codex")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) { Write-Output "[PASS] $cmd -> $($found.Source)" }
    else        { Add-Failure "$cmd - not found" }
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
    $path = $t.Source
    $name = $t.Name

    if (-not (Test-Path $path)) {
        Add-Failure "$name - file not found at $path"
        continue
    }
    $content = Get-Content $path -Raw

    if ($t.Format -eq "JSON") {
        try {
            $j = $content | ConvertFrom-Json
        } catch {
            Add-Failure "$name - Invalid JSON: $_"
            continue
        }
        $servers = $j.$($t.ServerKey)
        if (-not $servers) {
            Add-Failure "$name - No $($t.ServerKey) key found"
            continue
        }
        $entry = $servers.$ServerName
        if (-not $entry) {
            $names = $servers.PSObject.Properties.Name -join ", "
            Add-Failure "$name - $ServerName missing (have: $names)"
            continue
        }
        $expected = $t.Desired
        # Normalized comparison
        if ($entry.command -ne $expected.command) {
            Add-Failure "$name - command mismatch: expected '$($expected.command)', got '$($entry.command)'"
            continue
        }
        $aArgs = ($entry.args -join " ")
        $eArgs = ($expected.args -join " ")
        if ($aArgs -ne $eArgs) {
            Add-Failure "$name - args mismatch: expected '$eArgs', got '$aArgs'"
            continue
        }
        if ($expected.type -and $entry.type -ne $expected.type) {
            Add-Failure "$name - type mismatch: expected '$($expected.type)', got '$($entry.type)'"
            continue
        }
        Write-Output "[PASS] $name - $ServerName correct [$aArgs]"
    }

    elseif ($t.Format -eq "TOML") {
        # Validate TOML syntax
        try {
            $result = python -c "import pathlib,tomllib; tomllib.loads(pathlib.Path(r'$path').read_text(encoding='utf-8')); print('OK')" 2>&1
            if ($LASTEXITCODE -ne 0) {
                Add-Failure "$name - TOML parse error: $result"
                continue
            }
        } catch {
            Add-Failure "$name - TOML error: $_"
            continue
        }
        # Check for expected section
        if ($content -match "\[mcp_servers\.$ServerName\]") {
            # Check for --isolated and correct package using regex
            if ($content -match "\[mcp_servers\.$ServerName\]" -and
                $content -match "\[mcp_servers\.$ServerName\][\s\S]*?--isolated" -and
                $content -match "\[mcp_servers\.$ServerName\][\s\S]*?$([regex]::Escape($Package))") {
                Write-Output "[PASS] $name - $ServerName section correct"
            } else {
                Add-Failure "$name - $ServerName section exists but missing --isolated or wrong package"
            }
        } else {
            Add-Failure "$name - $ServerName section missing"
        }
    }

    elseif ($t.Format -eq "YAML") {
        $mtchs = [regex]::Matches($content, "^mcpServers:", [System.Text.RegularExpressions.RegexOptions]::Multiline)
        if ($mtchs.Count -eq 1) {
            if ($content -match "name: $ServerName") {
                # Check for --isolated and correct package in the block
                $namePos = $content.IndexOf("name: $ServerName")
                $blockEnd = $content.IndexOf("slashCommands:", $namePos)
                if ($blockEnd -lt 0) { $blockEnd = $content.IndexOf("- name:", $namePos + 10) }
                if ($blockEnd -lt 0) { $blockEnd = $content.Length }
                $block = $content.Substring($namePos, $blockEnd - $namePos)
                if ($block -match "--isolated" -and $block -match $Package) {
                    Write-Output "[PASS] $name - mcpServers with $ServerName correct"
                } else {
                    Add-Failure "$name - $ServerName exists but missing --isolated or wrong package"
                }
            } else {
                Add-Failure "$name - mcpServers exists but no $ServerName found"
            }
        } elseif ($mtchs.Count -eq 0) {
            Add-Failure "$name - No mcpServers key found"
        } else {
            Add-Failure "$name - Duplicate mcpServers keys ($($mtchs.Count))"
        }
    }
}
Write-Output ""

# --- Workspace Duplicates ---
Write-Output "--- Workspace Duplicates ---"
$repoRoot = Split-Path -Parent $PSScriptRoot
$wf1 = Join-Path $repoRoot ".vscode\mcp.json"
if (Test-Path $wf1) {
    $wc = Get-Content $wf1 -Raw
    if ($wc -match "playwright") { Add-Failure "$wf1 - still has playwright entry" }
    else { Write-Output "[PASS] $wf1 - clean" }
}
$wf2 = Join-Path $repoRoot ".continue\mcpServers"
if (Test-Path $wf2) { Add-Failure "$wf2 - exists (should be removed)" }
else { Write-Output "[PASS] $wf2 - absent" }
$wf3 = Join-Path $repoRoot ".codex\config.toml"
if (Test-Path $wf3) { Add-Failure "$wf3 - exists (should be removed)" }
else { Write-Output "[PASS] $wf3 - absent" }

Write-Output ""
Write-Output "=== Summary ==="
Write-Output "Configuration targets: 4"
Write-Output "Runtime surfaces: 5 (VS Code, Cursor, Codex, Continue in VS Code, Continue in Cursor)"
if ($failures.Count -gt 0) {
    Write-Output "Failures: $($failures.Count)"
    $failures | ForEach-Object { Write-Output "  - $_" }
    Write-Output "`n=== VERIFICATION FAILED ==="
    exit 1
} else {
    Write-Output "All checks passed."
    Write-Output "`n=== VERIFICATION PASSED ==="
    exit 0
}
