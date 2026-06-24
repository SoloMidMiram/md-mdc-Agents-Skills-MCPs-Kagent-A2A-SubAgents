<#
.SYNOPSIS
    Verify playwright-global MCP configuration across all registered hosts.
#>

$ErrorActionPreference = "Continue"
$ServerName = "playwright-global"
$Package = "@playwright/mcp@0.0.76"

Write-Output "=== playwright-global Verifier ==="
Write-Output ""

Write-Output "--- Command Availability ---"
foreach ($cmd in @("node","npm","npx","code","cursor","codex")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) { Write-Output "[PASS] $cmd -> $($found.Source)" }
    else        { Write-Output "[FAIL] $cmd - not found" }
}
Write-Output ""

Write-Output "--- Package ---"
try {
    $help = npx -y "$Package" --help 2>&1 | Select-String -Pattern "Usage:" -Quiet
    if ($help) { Write-Output "[PASS] $Package - available" }
    else       { Write-Output "[WARN] $Package - unexpected output" }
} catch {
    Write-Output "[FAIL] $Package - error: $_"
}
Write-Output ""

Write-Output "--- Host Configuration ---"
$hosts = @(
    @{ Name = "Cursor native"; Path = "C:\Users\cebit.ir\.cursor\mcp.json"; Type = "JSON" }
    @{ Name = "Codex"; Path = "C:\Users\cebit.ir\.codex\config.toml"; Type = "TOML" }
    @{ Name = "Continue"; Path = "C:\Users\cebit.ir\.continue\config.yaml"; Type = "YAML" }
    @{ Name = "VS Code native"; Path = "$env:APPDATA\Code\User\mcp.json"; Type = "JSON" }
)

foreach ($h in $hosts) {
    if (-not (Test-Path $h.Path)) {
        Write-Output "[MISSING] $($h.Name) - $($h.Path) not found"
        continue
    }
    $content = Get-Content $h.Path -Raw

    if ($h.Type -eq "JSON") {
        try {
            $j = $content | ConvertFrom-Json
            $servers = $j.servers
            if (-not $servers) { $servers = $j.mcpServers }
            if ($servers.$ServerName) {
                $argsLine = ($servers.$ServerName.args) -join " "
                Write-Output "[PASS] $($h.Name) - $ServerName found [$argsLine]"
            } else {
                $names = $servers.PSObject.Properties.Name -join ", "
                Write-Output "[FAIL] $($h.Name) - $ServerName missing (have: $names)"
            }
        } catch {
            Write-Output "[FAIL] $($h.Name) - Invalid JSON: $_"
        }
    } elseif ($h.Type -eq "TOML") {
        try {
            $result = python -c "import pathlib,tomllib; tomllib.loads(pathlib.Path(r'$($h.Path)').read_text(encoding='utf-8')); print('OK')" 2>&1
            if ($content -match "\[mcp_servers\.$ServerName\]") {
                Write-Output "[PASS] $($h.Name) - $ServerName section found"
            } else {
                Write-Output "[FAIL] $($h.Name) - $ServerName section missing"
            }
        } catch {
            Write-Output "[FAIL] $($h.Name) - TOML error: $_"
        }
    } elseif ($h.Type -eq "YAML") {
        $mtchs = [regex]::Matches($content, "^mcpServers:", [System.Text.RegularExpressions.RegexOptions]::Multiline)
        if ($mtchs.Count -eq 1) {
            if ($content -match "name: $ServerName") {
                Write-Output "[PASS] $($h.Name) - mcpServers with $ServerName found"
            } else {
                Write-Output "[FAIL] $($h.Name) - mcpServers exists but no $ServerName"
            }
        } elseif ($mtchs.Count -eq 0) {
            Write-Output "[FAIL] $($h.Name) - No mcpServers key found"
        } else {
            Write-Output "[FAIL] $($h.Name) - Duplicate mcpServers ($($mtchs.Count))"
        }
    }
}
Write-Output ""

Write-Output "--- Workspace Duplicates ---"
$wf1 = "F:\Git\MCPtest\.vscode\mcp.json"
if (Test-Path $wf1) {
    $wc = Get-Content $wf1 -Raw
    if ($wc -match "playwright") { Write-Output "[WARN] $wf1 - still has playwright entry" }
    else { Write-Output "[PASS] $wf1 - clean" }
}
$wf2 = "F:\Git\MCPtest\.continue\mcpServers"
if (Test-Path $wf2) { Write-Output "[WARN] $wf2 - exists" }
else { Write-Output "[PASS] $wf2 - absent" }
$wf3 = "F:\Git\MCPtest\.codex\config.toml"
if (Test-Path $wf3) { Write-Output "[WARN] $wf3 - exists" }
else { Write-Output "[PASS] $wf3 - absent" }

Write-Output ""
Write-Output "=== Verification Complete ==="
