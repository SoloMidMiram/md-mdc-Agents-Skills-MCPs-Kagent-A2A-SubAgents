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
.EXAMPLE
    .\install-global-playwright-mcp.ps1
.EXAMPLE
    .\install-global-playwright-mcp.ps1 -WhatIf
#>

param([switch]$WhatIf)

$ErrorActionPreference = "Stop"

# Load shared config target manifest
. "$PSScriptRoot\McpConfigTargets.ps1"

Write-Output "=== playwright-global Installer (WhatIf=$WhatIf) ==="
Write-Output "Package: $Package`n"

# --- Phase 1: Inspect all targets and compute planned changes ---
Write-Output "--- Inspection ---"
$plan = @()  # each item: @{Target = $t; Action = "create|update|skip|exists"; Reason = "..."}
foreach ($t in $Script:ConfigTargets) {
    $path = $t.Source
    if (-not (Test-Path $path)) {
        $plan += @{ Target = $t; Action = "skip"; Reason = "file not found" }
        continue
    }
    $actual = Get-ActualEntry $t
    if (-not $actual) {
        $plan += @{ Target = $t; Action = "create"; Reason = "$($Script:ServerName) not present" }
    } elseif (Test-EntryMatches $actual $t) {
        $plan += @{ Target = $t; Action = "exists"; Reason = "correct" }
    } else {
        $plan += @{ Target = $t; Action = "update"; Reason = "stale entry needs repair" }
    }
}

# Report plan
$changesNeeded = $plan | Where-Object { $_.Action -in @("create","update") }
foreach ($p in $plan) {
    $verb = switch ($p.Action) { "create" { "CREATE" } "update" { "UPDATE" } "exists" { "EXISTS" } "skip" { "SKIP" } }
    Write-Output "[$verb] $($p.Target.Name) - $($p.Reason)"
}

# --- Phase 2: If WhatIf or no changes needed, stop here ---
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

# --- Phase 3: Create backup and apply changes ---
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
        # Safe-create server container key
        if (-not $j.$($t.ServerKey)) {
            $j | Add-Member -MemberType NoteProperty -Name $t.ServerKey -Value @{} -Force
        }
        $entry = @{ command = $t.DesiredCommand; args = @($t.DesiredArgs) }
        if ($t.DesiredType) { $entry.type = $t.DesiredType }
        $j.$($t.ServerKey).$ServerName = $entry
        $j | ConvertTo-Json -Depth 5 | Set-Content $path -Encoding UTF8
        Write-Output "[$($p.Action.ToUpper())] $($t.Name)"
        $changed++
    }

    elseif ($t.Format -eq "TOML") {
        $content = Get-Content $path -Raw
        if ($content -match "\[mcp_servers\.$ServerName\]") {
            # Replace existing section line by line-safe regex
            $content = $content -replace "(?m)^\[mcp_servers\.$ServerName\].*?(?:^\[|$)", ""
        }
        $block = "`n[mcp_servers.$ServerName]`ncommand = ""$($t.DesiredCommand)""`nargs = [""-y"", ""$Package"", ""--isolated""]"
        $content += $block
        Set-Content $path -Value $content -Encoding UTF8
        Write-Output "[$($p.Action.ToUpper())] $($t.Name)"
        $changed++
    }

    elseif ($t.Format -eq "YAML") {
        $content = Get-Content $path -Raw
        $newEntry = @"
  - name: $ServerName
    type: $($t.DesiredType)
    command: $($t.DesiredCommand)
    args:
      - "-y"
      - "$Package"
      - "--isolated"
"@
        if ($content -match "^mcpServers:") {
            if ($content -match "name: $ServerName") {
                # Replace existing stale entry using line-based approach
                $namePos = $content.IndexOf("name: $ServerName")
                $before = $content.Substring(0, $namePos)
                $itemStart = $before.LastIndexOf("`n  - name:")
                if ($itemStart -lt 0) { $itemStart = $before.LastIndexOf("mcpServers:") }
                if ($itemStart -lt 0) { Write-Output "[FAIL] $($t.Name) - cannot locate entry boundary"; continue }
                $after = $content.Substring($itemStart)
                $nextItem = $after.IndexOf("`n  - name:", [Math]::Max($after.IndexOf("`n", 1), 1))
                $itemEnd = if ($nextItem -ge 0) { $itemStart + $nextItem } else { $content.Length }
                $content = $content.Substring(0, $itemStart) + "mcpServers:`n" + $newEntry + "`n" + $content.Substring($itemEnd)
            } else {
                # Append to existing list — after the last existing entry
                $lastEntry = $content.LastIndexOf("  - name:")
                $insertPos = $content.IndexOf("`n", $lastEntry)
                if ($insertPos -le 0) { $insertPos = $content.IndexOf("mcpServers:") + 12 }
                $content = $content.Substring(0, $insertPos) + "`n" + $newEntry + $content.Substring($insertPos)
            }
        } else {
            # Insert before slashCommands: or at end
            $newBlock = "mcpServers:`n$newEntry`n"
            $insert = $content.IndexOf("slashCommands:")
            if ($insert -ge 0) {
                $content = $content.Substring(0, $insert) + $newBlock + $content.Substring($insert)
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
