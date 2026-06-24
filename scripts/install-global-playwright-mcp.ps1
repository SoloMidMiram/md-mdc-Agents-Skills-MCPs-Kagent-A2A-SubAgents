<#
.SYNOPSIS
    Install/update playwright-global MCP server across all registered local hosts.
.DESCRIPTION
    Convergent installer that registers playwright-global (pinned @playwright/mcp@0.0.76,
    --isolated) in VS Code user, Cursor user, Codex user, and Continue user configs.
    
    Convergent behavior:
    - Absent       -> create
    - Correct      -> no change (reported as EXISTS)
    - Incorrect    -> update after backup
    - Malformed    -> fail safely with explanation
    - Unavailable  -> skip only when explicitly allowed
    
    Creates timestamped backups before any change. Supports -WhatIf dry-run mode.
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

# Backup
$bkDir = New-BackupDir
Write-Output "=== playwright-global Installer (WhatIf=$WhatIf) ==="
Write-Output "Package: $Package`n"

# --- Backups ---
Write-Output "--- Backups (backup dir: $bkDir) ---"
Backup-ConfigTargets -BackupDir $bkDir -WhatIf:$WhatIf

# --- Implementation ---
Write-Output "`n--- Implementation ---"
$changed = 0

foreach ($t in $Script:ConfigTargets) {
    $path = $t.Source
    if ($WhatIf) { Write-Output "[WHATIF] Would process $($t.Name) at $path"; continue }

    if (-not (Test-Path $path)) {
        Write-Output "[SKIP] $($t.Name) - file not found at $path"
        continue
    }

    if ($t.Format -eq "JSON") {
        try {
            $j = Get-Content $path -Raw | ConvertFrom-Json
        } catch {
            Write-Output "[FAIL] $($t.Name) - cannot parse JSON: $_"
            continue
        }
        $servers = $j.$($t.ServerKey)
        $existing = $servers.$ServerName
        $expected = Get-ExpectedEntry $t

        if ($existing) {
            if (Test-EntryMatches $existing $expected) {
                Write-Output "[EXISTS] $($t.Name) - $ServerName correct"
            } else {
                Write-Output "[UPDATE] $($t.Name) - $ServerName exists but needs repair"
                Backup-ConfigTargets -BackupDir $bkDir -WhatIf:$false | Out-Null
                $servers.$ServerName = $expected
                $j | ConvertTo-Json -Depth 5 | Set-Content $path -Encoding UTF8
                $changed++
            }
        } else {
            Write-Output "[CREATE] $($t.Name) - adding $ServerName"
            $servers | Add-Member -MemberType NoteProperty -Name $ServerName -Value $expected -Force
            $j | ConvertTo-Json -Depth 5 | Set-Content $path -Encoding UTF8
            $changed++
        }
    }

    elseif ($t.Format -eq "TOML") {
        $content = Get-Content $path -Raw
        if ($content -match "\[mcp_servers\.$ServerName\]") {
            # Check if args contain --isolated and correct package
            if ($content -match "\[mcp_servers\.$ServerName\][\s\S]*?--isolated" -and
                $content -match "\[mcp_servers\.$ServerName\][\s\S]*?$Package") {
                Write-Output "[EXISTS] $($t.Name) - $ServerName correct"
            } else {
                Write-Output "[UPDATE] $($t.Name) - replacing stale $ServerName"
                # Remove old section and add new one
                $content = $content -replace "(?ms)\[mcp_servers\.$ServerName\].*?(?=\[|$)", ""
                $block = "`n[mcp_servers.$ServerName]`ncommand = ""npx""`nargs = [""-y"", ""$Package"", ""--isolated""]"
                $content += $block
                Set-Content $path -Value $content -Encoding UTF8
                $changed++
            }
        } else {
            Write-Output "[CREATE] $($t.Name) - adding $ServerName"
            $block = "`n[mcp_servers.$ServerName]`ncommand = ""npx""`nargs = [""-y"", ""$Package"", ""--isolated""]"
            $content += $block
            Set-Content $path -Value $content -Encoding UTF8
            $changed++
        }
    }

    elseif ($t.Format -eq "YAML") {
        $content = Get-Content $path -Raw
        $hasMcpServers = $content -match "^mcpServers:"
        if ($hasMcpServers) {
            if ($content -match "name: $ServerName") {
                Write-Output "[EXISTS] $($t.Name) - $ServerName correct"
            } else {
                Write-Output "[UPDATE] $($t.Name) - adding $ServerName to existing mcpServers"
                # Append to existing mcpServers list
                $block = "  - name: $ServerName`n    type: stdio`n    command: npx`n    args:`n      - `"-y`"`n      - `"$Package`"`n      - `"--isolated`""
                $content = $content -replace "(mcpServers:\s*\n)", "`$1$block`n"
                Set-Content $path -Value $content -Encoding UTF8
                $changed++
            }
        } else {
            Write-Output "[CREATE] $($t.Name) - adding mcpServers block"
            $newYaml = @"
mcpServers:
  - name: $ServerName
    type: stdio
    command: npx
    args:
      - "-y"
      - "$Package"
      - "--isolated"

"@
            # Find a safe insertion point: before slashCommands: or at end of file
            $insert = $content.IndexOf("slashCommands:")
            if ($insert -ge 0) {
                $content = $content.Substring(0, $insert) + $newYaml + $content.Substring($insert)
            } else {
                # Append at end
                $content += "`n" + $newYaml
            }
            Set-Content $path -Value $content -Encoding UTF8
            $changed++
        }
    }
}

Write-Output "`n=== Complete ==="
Write-Output "Backup directory: $bkDir"
Write-Output "Configurations changed: $changed"
if ($changed -eq 0) {
    Write-Output "All configurations already correct."
}
if (-not $WhatIf) {
    Write-Output "Run .\verify-global-playwright-mcp.ps1 to validate."
}
