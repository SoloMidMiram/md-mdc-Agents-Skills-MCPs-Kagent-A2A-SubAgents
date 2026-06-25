<#
.SYNOPSIS
    Shared MCP configuration target manifest for installer, rollback, and verifier.
.DESCRIPTION
    Single source of truth for MCP host configurations.
    All four targets now carry normalized DesiredCommand, DesiredArgs, and
    DesiredType fields so that any format can be compared through a single
    normalized Test-EntryMatches function.
#>

$Script:ServerName = "playwright-global"
$Script:Package = "@playwright/mcp@0.0.76"
$Script:DesiredArgs = @("-y", $Script:Package, "--isolated")
$Script:DesiredCommand = "npx"

$Script:ConfigTargets = @(
    @{
        Name          = "Cursor"
        Source        = Join-Path $env:USERPROFILE ".cursor\mcp.json"
        BackupName    = "cursor-mcp.json"
        Format        = "JSON"
        ServerKey     = "mcpServers"
        DesiredCommand= $Script:DesiredCommand
        DesiredArgs   = $Script:DesiredArgs
        DesiredType   = $null
    }
    @{
        Name          = "Codex"
        Source        = Join-Path $env:USERPROFILE ".codex\config.toml"
        BackupName    = "codex-config.toml"
        Format        = "TOML"
        ServerKey     = $null
        DesiredCommand= $Script:DesiredCommand
        DesiredArgs   = $Script:DesiredArgs
        DesiredType   = $null
    }
    @{
        Name          = "Continue"
        Source        = Join-Path $env:USERPROFILE ".continue\config.yaml"
        BackupName    = "continue-config.yaml"
        Format        = "YAML"
        ServerKey     = $null
        DesiredCommand= $Script:DesiredCommand
        DesiredArgs   = $Script:DesiredArgs
        DesiredType   = "stdio"
    }
    @{
        Name          = "VS Code"
        Source        = Join-Path $env:APPDATA "Code\User\mcp.json"
        BackupName    = "vscode-user-mcp.json"
        Format        = "JSON"
        ServerKey     = "servers"
        DesiredCommand= $Script:DesiredCommand
        DesiredArgs   = $Script:DesiredArgs
        DesiredType   = "stdio"
    }
)

$Script:BackupRoot = Join-Path $env:USERPROFILE ".mcp-config-backups"

# --- Typed State Constants ---
$Script:StateFileMissing   = "FILE_MISSING"
$Script:StateEntryMissing  = "ENTRY_MISSING"
$Script:StateEntryCorrect  = "ENTRY_CORRECT"
$Script:StateEntryStale    = "ENTRY_STALE"
$Script:StateFileMalformed = "FILE_MALFORMED"

function Get-ConfigState {
    <#
    .SYNOPSIS
      Returns the typed state of a config target.
      Returns one of: FILE_MISSING, FILE_MALFORMED, ENTRY_MISSING, ENTRY_CORRECT, ENTRY_STALE
    .PARAMETER Target
      A config target from $Script:ConfigTargets.
    #>
    param($Target)
    if (-not (Test-Path $Target.Source)) { return $Script:StateFileMissing }

    # Check parseability before checking entry
    $content = Get-Content $Target.Source -Raw -ErrorAction SilentlyContinue
    if (-not $content) { return $Script:StateFileMalformed }

    if ($Target.Format -eq "JSON") {
        try { $null = $content | ConvertFrom-Json } catch { return $Script:StateFileMalformed }
    }
    # TOML and YAML: rely on Get-ActualEntry internal error handling since
    # we don't have a native TOML/YAML parser in PowerShell.

    $actual = Get-ActualEntry $Target
    if (-not $actual) { return $Script:StateEntryMissing }
    if (Test-EntryMatches $actual $Target) { return $Script:StateEntryCorrect }
    return $Script:StateEntryStale
}

function New-BackupDir {
    param([switch]$WhatIf)
    if ($WhatIf) { return "[WHATIF] $Script:BackupRoot\<TIMESTAMP>" }
    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    $dir = Join-Path $Script:BackupRoot $ts
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    return $dir
}

function Backup-ConfigTargets {
    param([string]$BackupDir, [string[]]$AffectedTargets, [switch]$WhatIf)
    $targetsToBackup = if ($AffectedTargets) { $Script:ConfigTargets | Where-Object { $_.Name -in $AffectedTargets } } else { $Script:ConfigTargets }
    foreach ($t in $targetsToBackup) {
        if (-not (Test-Path $t.Source)) {
            Write-Output "[SKIP] $($t.Name) - file not found at $($t.Source)"
            continue
        }
        $dest = Join-Path $BackupDir $t.BackupName
        if (-not $WhatIf) {
            Copy-Item $t.Source $dest -Force
            $hash = (Get-FileHash $t.Source -Algorithm SHA256).Hash
            "$($t.BackupName) | $hash | $($t.Source)" | Out-File (Join-Path $BackupDir "manifest-sha256.txt") -Append -Encoding UTF8
        }
        Write-Output "[BACKUP] $($t.Name) -> $dest"
    }
}

function Get-ActualEntry {
    <#
    .SYNOPSIS
      Reads the current config file and returns a hashtable with command, args,
      and type suitable for Test-EntryMatches.
      Returns $null if the target does not have a playwright-global entry.
    #>
    param($Target)
    if (-not (Test-Path $Target.Source)) { return $null }
    $content = Get-Content $Target.Source -Raw

    if ($Target.Format -eq "JSON") {
        try { $j = $content | ConvertFrom-Json } catch { return $null }
        $container = $j.$($Target.ServerKey)
        if (-not $container) { return $null }
        $entry = $container.$Script:ServerName
        if (-not $entry) { return $null }
        return @{
            command = $entry.command
            args    = if ($entry.args) { @($entry.args) } else { @() }
            type    = $entry.type
        }
    }

    if ($Target.Format -eq "TOML") {
        if ($content -notmatch "\[mcp_servers\.$Script:ServerName\]") { return $null }
        $posixPath = $Target.Source -replace '\\', '/'
        $pyScript = "import pathlib, json, importlib, importlib.util; tomllib = __import__('tomllib') if importlib.util.find_spec('tomllib') else __import__('tomli'); p = pathlib.Path(r'PATH'); text = p.read_text(encoding='utf-8'); data = tomllib.loads(text); entry = data.get('mcp_servers', {}).get('SERVER'); print(json.dumps(entry))"
        $pyScript = $pyScript.Replace('PATH', $posixPath).Replace('SERVER', $Script:ServerName)
        try {
            $jsonOutput = & python -c $pyScript 2>$null
            if ($LASTEXITCODE -ne 0 -or -not $jsonOutput) { return $null }
            $parsed = $jsonOutput | ConvertFrom-Json
            return @{ command = $parsed.command; args = @($parsed.args); type = $parsed.type }
        } catch {
            return $null
        }
    }

    if ($Target.Format -eq "YAML") {
        # Normalize CRLF to LF for line-anchored parsing
        $content = $content -replace "`r`n", "`n"
        if ($content -notmatch "name: $Script:ServerName") { return $null }
        $namePos = $content.IndexOf("name: $Script:ServerName")
        # Find start of this list item: go backward to previous `  - name:` or `mcpServers:`
        $before = $content.Substring(0, $namePos)
        $itemStart = $before.LastIndexOf("`n  - name:")
        if ($itemStart -lt 0) { $itemStart = $before.LastIndexOf("mcpServers:") }
        if ($itemStart -lt 0) { return $null }
        # Find end of this list item: search FORWARD from namePos for next `  - name:`
        $afterName = $content.Substring($namePos)
        $nextItem = $afterName.IndexOf("`n  - name:", 1)  # skip the first match which is ourselves
        $itemEnd = if ($nextItem -ge 0) { $namePos + $nextItem } else { $content.Length }
        $block = $content.Substring($itemStart, $itemEnd - $itemStart)
        # Extract fields
        $cmd = if ($block -match "command:\s*(\S+)") { $matches[1] } else { $null }
        $type = if ($block -match "type:\s*(\S+)") { $matches[1] } else { $null }
        # Extract args
        $argsBlock = [regex]::Match($block, "(?s)args:\n((?:\s+-.*\n?)*)")
        $args = if ($argsBlock.Success) {
            [regex]::Matches($argsBlock.Groups[1].Value, '- "(.*?)"') | ForEach-Object { $_.Groups[1].Value }
        } else { @() }
        return @{ command = $cmd; args = @($args); type = $type }
    }

    return $null
}

function Test-EntryMatches {
    <#
    .SYNOPSIS
      Compares a hashtable entry (from Get-ActualEntry) against the desired
      command, args, and optional type for a target.
    #>
    param($Actual, $Target)
    if (-not $Actual) { return $false }
    if ($Actual.command -ne $Target.DesiredCommand) { return $false }
    $aArgs = $Actual.args -join " "
    $eArgs = $Target.DesiredArgs -join " "
    if ($aArgs -ne $eArgs) { return $false }
    if ($Target.DesiredType -and $Actual.type -ne $Target.DesiredType) { return $false }
    return $true
}
