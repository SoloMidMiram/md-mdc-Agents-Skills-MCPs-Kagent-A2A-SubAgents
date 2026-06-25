<#
.SYNOPSIS
    Install/update playwright-global MCP server across all registered local hosts.
.DESCRIPTION
    Convergent installer — creates, repairs, or skips depending on current state.
    
    Convergent behavior:
    - Absent         -> create
    - Correct        -> no change (reported as EXISTS)
    - Incorrect      -> update after backup
    - Malformed      -> fail safely with explanation
    - Unavailable    -> skip with message
    
    Creates timestamped backups only when at least one change is needed.
    -WhatIf is truly non-mutating — no backup directory or files created.
.PARAMETER WhatIf
    Show what would change without making any edits.
.PARAMETER ConfigRoot
    Override config root for testing. If provided, all config file paths are rebased
    to this directory instead of the real user profile.
.EXAMPLE
    .\install-global-playwright-mcp.ps1
.EXAMPLE
    .\install-global-playwright-mcp.ps1 -WhatIf
.EXAMPLE
    .\install-global-playwright-mcp.ps1 -ConfigRoot C:\Temp\TestWorkspace
#>

param(
    [switch]$WhatIf,
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

Write-Output "=== playwright-global Installer (WhatIf=$WhatIf) ==="
Write-Output "Package: $Package`n"

# --- Phase 1: Inspect all targets and compute planned changes ---
Write-Output "--- Inspection ---"
$plan = @()  # each item: @{Target = $t; Action = "create|update|skip|exists|malformed"; Reason = "..."}
$hasMalformed = $false
foreach ($t in $Script:ConfigTargets) {
    $state = Get-ConfigState $t
    switch ($state) {
        $Script:StateFileMissing {
            $plan += @{ Target = $t; Action = "skip"; Reason = "file not found" }
        }
        $Script:StateFileMalformed {
            $plan += @{ Target = $t; Action = "malformed"; Reason = "file is corrupted or unparseable" }
            $hasMalformed = $true
        }
        $Script:StateDependencyMissing {
            $plan += @{ Target = $t; Action = "malformed"; Reason = "Python is required for TOML/YAML validation but not found on PATH" }
            $hasMalformed = $true
        }
        $Script:StateEntryMissing {
            $plan += @{ Target = $t; Action = "create"; Reason = "$($Script:ServerName) not present" }
        }
        $Script:StateEntryCorrect {
            $plan += @{ Target = $t; Action = "exists"; Reason = "correct" }
        }
        $Script:StateEntryStale {
            $plan += @{ Target = $t; Action = "update"; Reason = "stale entry needs repair" }
        }
    }
}

# Report plan
$changesNeeded = $plan | Where-Object { $_.Action -in @("create","update") }
foreach ($p in $plan) {
    $verb = switch ($p.Action) {
        "create"    { "CREATE" }
        "update"    { "UPDATE" }
        "exists"    { "EXISTS" }
        "skip"      { "SKIP" }
        "malformed" { "MALFORMED" }
    }
    Write-Output "[$verb] $($p.Target.Name) - $($p.Reason)"
}

# --- Phase 2: Exit early for malformed files (before any mutation) ---
if ($hasMalformed) {
    Write-Output "`n[FAIL] One or more config files are malformed or unparseable. Fix them manually before retrying."
    Write-Output "=== ABORTED ==="
    exit 1
}

# --- Phase 3: If WhatIf or no changes needed, stop here ---
if ($WhatIf) {
    if ($changesNeeded.Count -gt 0) {
        Write-Output "`n[WHATIF] Would create backup and apply $($changesNeeded.Count) change(s)."
    } else {
        Write-Output "`n[WHATIF] No changes needed."
    }
    Write-Output "`n=== Dry-run Complete ==="
    exit 0
}

if ($changesNeeded.Count -eq 0) {
    Write-Output "`nNo changes needed. All configurations already correct."
    Write-Output "=== Complete ==="
    exit 0
}

# --- Phase 4: Create backup and apply changes ---
$affectedNames = $changesNeeded | ForEach-Object { $_.Target.Name }
$bkDir = New-BackupDir
Write-Output "`n--- Backups (backup dir: $bkDir) ---"
Backup-ConfigTargets -BackupDir $bkDir -AffectedTargets $affectedNames

Write-Output "`n--- Applying $($changesNeeded.Count) change(s) ---"
$changed = 0

foreach ($p in $changesNeeded) {
    $t = $p.Target
    $path = $t.Source

    if ($t.Format -eq "JSON") {
        try { $j = Get-Content $path -Raw | ConvertFrom-Json } catch {
            Write-Output "[FAIL] $($t.Name) - cannot parse JSON: $_"; continue
        }
        # Safe-create server container key using Add-Member -Force (works in PS 5.1 and 7+)
        # Use [PSCustomObject]@{} so nested Add-Member works on the container value
        if (-not $j.$($t.ServerKey)) {
            $j | Add-Member -MemberType NoteProperty -Name $t.ServerKey -Value ([PSCustomObject]@{}) -Force
        }
        $entry = @{ command = $t.DesiredCommand; args = @($t.DesiredArgs) }
        if ($t.DesiredType) { $entry.type = $t.DesiredType }
        # Add the server entry using Add-Member for reliability on PSCustomObject
        $j.$($t.ServerKey) | Add-Member -MemberType NoteProperty -Name $ServerName -Value $entry -Force
        $j | ConvertTo-Json -Depth 5 | Set-Content $path -Encoding UTF8
        Write-Output "[$($p.Action.ToUpper())] $($t.Name)"
        $changed++
    }

    elseif ($t.Format -eq "TOML") {
        $content = Get-Content $path -Raw
        if ($content -match "\[mcp_servers\.$ServerName\]") {
            # Remove entire stale section (header + body) up to next section or end
            $content = $content -replace "(?s)\[mcp_servers\.$ServerName\].*?(?=\n\[|\z)", ""
        }
        $block = "`n[mcp_servers.$ServerName]`ncommand = ""$($t.DesiredCommand)""`nargs = [""-y"", ""$Package"", ""--isolated""]"
        $content += $block
        Set-Content $path -Value $content -Encoding UTF8
        Write-Output "[$($p.Action.ToUpper())] $($t.Name)"
        $changed++
    }

    elseif ($t.Format -eq "YAML") {
        $content = Get-Content $path -Raw
        # Normalize CRLF to LF for line-anchored boundary detection
        $content = $content -replace "`r`n", "`n"
        $newEntry = @"
  - name: $ServerName
    type: $($t.DesiredType)
    command: $($t.DesiredCommand)
    args:
      - "-y"
      - "$Package"
      - "--isolated"
"@
        # === Find mcpServers section boundaries ===
        $mcpPos = $content.IndexOf("mcpServers:")
        if ($mcpPos -ge 0) {
            # Find the next top-level YAML key generically to bound the section
            # Matches any `^word:` at start of a line after mcpServers:
            $afterMcp = $mcpPos + 12  # past "mcpServers:"
            $sectionEnd = $content.Length
            $nextKeyMatch = [regex]::Match($content, "(?m)^[a-zA-Z_][a-zA-Z0-9_/-]*:", $afterMcp)
            if ($nextKeyMatch.Success -and $nextKeyMatch.Index -gt $afterMcp) {
                $sectionEnd = $nextKeyMatch.Index
            }
            # Work only inside the mcpServers section
            $section = $content.Substring($mcpPos, $sectionEnd - $mcpPos)
            $sectionNamePos = $section.IndexOf("name: $ServerName")
            if ($sectionNamePos -ge 0) {
                # Replace existing stale entry — find item boundaries within the section
                # Include enough context so LastIndexOf finds the complete \n  - name:
                $beforeEnd = $sectionNamePos + 5  # include up to the ':' in 'name:'
                $before = $section.Substring(0, [Math]::Min($beforeEnd, $section.Length))
                $itemStartRel = $before.LastIndexOf("`n  - name:")
                if ($itemStartRel -lt 0) { $itemStartRel = 0 }
                $afterName = $section.Substring($sectionNamePos)
                $nextItem = $afterName.IndexOf("`n  - name:", 1)
                $itemEndRel = if ($nextItem -ge 0) { $sectionNamePos + $nextItem } else { $section.Length }
                # Replace the list item within the section slice
                $newSection = $section.Substring(0, $itemStartRel) + "`n" + $newEntry + "`n" + $section.Substring($itemEndRel)
                $content = $content.Substring(0, $mcpPos) + $newSection + $content.Substring($sectionEnd)
            } else {
                # Append to existing mcpServers list at the end of the bounded section
                $trailing = if ($sectionEnd -lt $content.Length) { $content.Substring($sectionEnd) } else { "" }
                $newSection = $section.TrimEnd() + "`n" + $newEntry + "`n"
                $content = $content.Substring(0, $mcpPos) + $newSection + $trailing
            }
        } else {
            # mcpServers section does not exist — find the first top-level key to insert before
            $firstKeyMatch = [regex]::Match($content, "(?m)^[a-zA-Z_][a-zA-Z0-9_/-]*:")
            $newBlock = "mcpServers:`n$newEntry`n"
            if ($firstKeyMatch.Success) {
                $content = $content.Substring(0, $firstKeyMatch.Index) + $newBlock + $content.Substring($firstKeyMatch.Index)
            } else {
                $content += "`n$newBlock"
            }
        }
        Set-Content $path -Value $content -Encoding UTF8
        Write-Output "[$($p.Action.ToUpper())] $($t.Name)"
        $changed++
    }
}

Write-Output "`n=== Complete ==="
Write-Output "Backup directory: $bkDir"
Write-Output "Configurations changed: $changed"
Write-Output "Run .\verify-global-playwright-mcp.ps1 to validate."
