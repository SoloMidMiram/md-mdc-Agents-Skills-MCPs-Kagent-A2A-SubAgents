<#
.SYNOPSIS
    Shared test helper module for the MCP evaluation framework.
.DESCRIPTION
    Provides fixture management, config parsing, and comparison utilities
    for Pester-based evaluation of playwright-global MCP infrastructure.
#>

# --- Fixture Management ---

$Script:FixtureDir = Join-Path $PSScriptRoot "fixtures"
$Script:DatasetDir = Join-Path $PSScriptRoot "dataset"

function Get-FixturePath {
    <#
    .SYNOPSIS
      Returns the path to a test fixture file.
    .PARAMETER Name
      Fixture name: "Cursor", "Codex", "Continue", or "VS Code"
    #>
    param([string]$Name)
    $map = @{
        "Cursor"   = "cursor-mcp-fixture.json"
        "Codex"    = "codex-config-fixture.toml"
        "Continue" = "continue-config-fixture.yaml"
        "VS Code"  = "vscode-mcp-fixture.json"
    }
    return Join-Path $Script:FixtureDir $map[$Name]
}

# --- Temp Workspace Management ---

$Script:TestRoot = $null

function New-TestWorkspace {
    <#
    .SYNOPSIS
      Creates a temporary directory with fixture configs for isolated testing.
      Returns the path. Call Remove-TestWorkspace to clean up.
    #>
    $tmp = Join-Path $env:TEMP "mcpeval-$([System.IO.Path]::GetRandomFileName())"
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $Script:TestRoot = $tmp
    return $tmp
}

function Remove-TestWorkspace {
    <#
    .SYNOPSIS
      Removes the temporary test workspace.
    #>
    if ($Script:TestRoot -and (Test-Path $Script:TestRoot)) {
        Remove-Item -Path $Script:TestRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    $Script:TestRoot = $null
}

function Deploy-Fixtures {
    <#
    .SYNOPSIS
      Copies all fixture files into a temporary directory structure
      that mirrors the real host locations.
    .PARAMETER Workspace
      Path to the test workspace root.
    #>
    param([string]$Workspace)
    $targets = @(
        @{ Name = "Cursor";   Rel = ".cursor\mcp.json" }
        @{ Name = "Codex";    Rel = ".codex\config.toml" }
        @{ Name = "Continue"; Rel = ".continue\config.yaml" }
        @{ Name = "VS Code";  Rel = "Code\User\mcp.json" }
    )
    foreach ($t in $targets) {
        $destDir = Join-Path $Workspace (Split-Path $t.Rel)
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        Copy-Item (Get-FixturePath $t.Name) (Join-Path $Workspace $t.Rel) -Force
    }
}

# --- Config Comparison ---

function Get-NormalizedEntry {
    <#
    .SYNOPSIS
      Reads a config file and returns a normalized hashtable with command, args, type.
      Supports JSON, TOML, and YAML formats.
    .PARAMETER Path
      Absolute path to the config file.
    .PARAMETER Format
      "JSON", "TOML", or "YAML"
    .PARAMETER ServerKey
      JSON container key (e.g., "mcpServers", "servers").
    #>
    param([string]$Path, [string]$Format, [string]$ServerKey = $null)
    if (-not (Test-Path $Path)) { return $null }
    $content = Get-Content $Path -Raw

    if ($Format -eq "JSON") {
        try { $j = $content | ConvertFrom-Json } catch { return $null }
        $container = if ($ServerKey) { $j.$ServerKey } else { $j }
        $entry = $container.'playwright-global'
        if (-not $entry) { return $null }
        return @{
            command = $entry.command
            args    = if ($entry.args) { @($entry.args) } else { @() }
            type    = $entry.type
        }
    }

    if ($Format -eq "TOML") {
        if ($content -notmatch '\[mcp_servers\.playwright-global\]') { return $null }
        $posixPath = $Path -replace '\\', '/'
        $pyScript = "import pathlib, json, importlib, importlib.util; spec = importlib.util.find_spec('tomllib'); tomllib = __import__('tomllib') if spec else __import__('tomli'); p = pathlib.Path(r'PATH'); text = p.read_text(encoding='utf-8'); data = tomllib.loads(text); entry = data.get('mcp_servers', {}).get('playwright-global'); print(json.dumps(entry))"
        $pyScript = $pyScript.Replace('PATH', $posixPath)
        try {
            $jsonOutput = & python -c $pyScript 2>$null
            if ($LASTEXITCODE -ne 0 -or -not $jsonOutput) { return $null }
            $parsed = $jsonOutput | ConvertFrom-Json
            return @{ command = $parsed.command; args = @($parsed.args); type = $parsed.type }
        } catch { return $null }
    }

    if ($Format -eq "YAML") {
        if ($content -notmatch 'name: playwright-global') { return $null }
        # Normalize line endings to LF for consistent regex matching
        $content = $content -replace "`r`n", "`n"
        # Find the mcpServers: section first, then locate the playwright-global entry within it
        $mcpPos = $content.IndexOf('mcpServers:')
        if ($mcpPos -lt 0) { return $null }
        # Find next top-level key after mcpServers: (to bound the section)
        $sectionEnd = $content.Length
        foreach ($bound in @("`nmodels:", "`nslashCommands:", "`nrules:", "`nexperimental:")) {
            $p = $content.IndexOf($bound, $mcpPos + 12)
            if ($p -gt 0 -and $p -lt $sectionEnd) { $sectionEnd = $p }
        }
        $section = $content.Substring($mcpPos, $sectionEnd - $mcpPos)
        # Within the section, find the playwright-global item and its fields
        $namePos = $section.IndexOf('name: playwright-global')
        if ($namePos -lt 0) { return $null }
        # Find end of this list item: next `  - name:` or section end
        $afterName = $section.Substring($namePos)
        $nextItem = $afterName.IndexOf("`n  - name:", 1)
        $itemEnd = if ($nextItem -ge 0) { $namePos + $nextItem } else { $section.Length }
        # Block starts at the beginning of the section (mcpServers:) so regexes
        # like command:, type:, args: can match within the mcpServers scope
        $block = $section.Substring(0, $itemEnd)
        $cmd = if ($block -match 'command:\s*(\S+)') { $matches[1] } else { $null }
        $type = if ($block -match 'type:\s*(\S+)') { $matches[1] } else { $null }
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
      Compares a normalized entry against the expected desired state.
    #>
    param(
        $Actual,
        [string]$ExpectedCommand = "npx",
        [string[]]$ExpectedArgs = @("-y", "@playwright/mcp@0.0.76", "--isolated"),
        [string]$ExpectedType = $null
    )
    if (-not $Actual) { return $false }
    if ($Actual.command -ne $ExpectedCommand) { return $false }
    if (($Actual.args -join " ") -ne ($ExpectedArgs -join " ")) { return $false }
    if ($ExpectedType -and $Actual.type -ne $ExpectedType) { return $false }
    return $true
}

# --- Backup/Rollback Helpers ---

function New-BackupDir {
    param([string]$Root)
    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    $dir = Join-Path $Root $ts
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    return $dir
}

function Backup-Files {
    param([string]$BackupDir, [hashtable[]]$FileMap)
    $manifest = @()
    foreach ($item in $FileMap) {
        if (-not (Test-Path $item.Source)) { continue }
        $dest = Join-Path $BackupDir $item.BackupName
        Copy-Item $item.Source $dest -Force
        $hash = (Get-FileHash $item.Source -Algorithm SHA256).Hash
        $manifest += "$($item.BackupName) | $hash"
    }
    $manifest | Out-File (Join-Path $BackupDir "manifest-sha256.txt") -Append -Encoding UTF8
}

function Restore-Files {
    param([string]$BackupDir, [hashtable[]]$FileMap)
    foreach ($item in $FileMap) {
        $src = Join-Path $BackupDir $item.BackupName
        if (-not (Test-Path $src)) { continue }
        Copy-Item $src $item.Source -Force
    }
}

function Get-FileHashSet {
    param([string[]]$Paths)
    $hash = @{}
    foreach ($p in $Paths) {
        if (Test-Path $p) {
            $hash[$p] = (Get-FileHash $p -Algorithm SHA256).Hash
        }
    }
    return $hash
}

# --- Dataset Helpers ---

function Get-EvalDataset {
    <#
    .SYNOPSIS
      Reads the evaluation dataset from JSONL and returns items as an array.
    #>
    $path = Join-Path $Script:DatasetDir "playwright-eval.jsonl"
    if (-not (Test-Path $path)) { return @() }
    $items = @()
    Get-Content $path | ForEach-Object {
        if ($_.Trim()) { $items += $_ | ConvertFrom-Json }
    }
    return $items
}

# --- Host Detection ---

function Test-HostAvailable {
    <#
    .SYNOPSIS
      Checks whether a given host tool is available on the system.
    #>
    param([string]$HostName)
    $cmdmap = @{
        "node"  = "node"
        "npm"   = "npm"
        "npx"   = "npx"
        "codex" = "codex"
        "code"  = "code"
        "cursor" = "cursor"
        "python" = "python"
    }
    $cmd = $cmdmap[$HostName]
    if (-not $cmd) { return $false }
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

Export-ModuleMember -Function * -Variable *
