<#
.SYNOPSIS
    Install/update playwright-global MCP server across all registered local hosts.
.DESCRIPTION
    Idempotent installer that registers playwright-global (pinned @playwright/mcp@0.0.76,
    --isolated) in VS Code user, Cursor user, Codex user, and Continue user configs.
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
$Package = "@playwright/mcp@0.0.76"
$ServerName = "playwright-global"

# Paths
$paths = @{
    Cursor   = "C:\Users\cebit.ir\.cursor\mcp.json"
    Codex    = "C:\Users\cebit.ir\.codex\config.toml"
    Continue = "C:\Users\cebit.ir\.continue\config.yaml"
    VSCode   = "$env:APPDATA\Code\User\mcp.json"
}

# Backup
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$bkDir = "C:\Users\cebit.ir\.mcp-config-backups\$ts"
if (-not $WhatIf) {
    New-Item -ItemType Directory -Path $bkDir -Force | Out-Null
}

function Backup-File {
    param($Path, $Label)
    if (Test-Path $Path) {
        $dest = Join-Path $bkDir "$Label-backup.json"
        if (-not $WhatIf) {
            Copy-Item $Path $dest -Force
            $hash = (Get-FileHash $Path -Algorithm SHA256).Hash
            "$Label | $Path | $hash" | Out-File (Join-Path $bkDir "backup-manifest.txt") -Append
        }
        Write-Output "[BACKUP] $Label → $dest"
    } else {
        Write-Output "[SKIP] $Label — file not found"
    }
}

Write-Output "=== playwright-global Installer (WhatIf=$WhatIf) ==="
Write-Output "Package: $Package`n"

# --- Backups ---
Write-Output "--- Backups ---"
Backup-File $paths.Cursor "cursor"
Backup-File $paths.Codex "codex"
Backup-File $paths.Continue "continue"
Backup-File $paths.VSCode "vscode-user"

# --- Implementation ---
Write-Output "`n--- Implementation ---"

# 1. Cursor
if ($WhatIf) { Write-Output "[WHATIF] Would update $($paths.Cursor)" }
else {
    $c = Get-Content $paths.Cursor -Raw | ConvertFrom-Json
    if ($c.mcpServers.$ServerName) {
        Write-Output "[EXISTS] Cursor — $ServerName already present"
    } else {
        $entry = @{ command = "npx"; args = @("-y", $Package, "--isolated") }
        $c.mcpServers | Add-Member -MemberType NoteProperty -Name $ServerName -Value $entry -Force
        $c | ConvertTo-Json -Depth 5 | Set-Content $paths.Cursor -Encoding UTF8
        Write-Output "[UPDATED] Cursor — added $ServerName"
    }
}

# 2. Codex
if ($WhatIf) { Write-Output "[WHATIF] Would update $($paths.Codex)" }
else {
    $t = Get-Content $paths.Codex -Raw
    if ($t -match "\[mcp_servers\.$ServerName\]") {
        Write-Output "[EXISTS] Codex — $ServerName already present"
    } else {
        $block = "`n[mcp_servers.$ServerName]`ncommand = ""npx""`nargs = [""-y"", ""$Package"", ""--isolated""]"
        $t += $block
        Set-Content $paths.Codex -Value $t -Encoding UTF8
        Write-Output "[UPDATED] Codex — added $ServerName"
    }
}

# 3. Continue
if ($WhatIf) { Write-Output "[WHATIF] Would update $($paths.Continue)" }
else {
    $y = Get-Content $paths.Continue -Raw
    if ($y -match "^mcpServers:") {
        if ($y -match "name: $ServerName") {
            Write-Output "[EXISTS] Continue — $ServerName already present"
        } else {
            Write-Output "[WARN] Continue has mcpServers but no $ServerName — manual merge needed"
        }
    } else {
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
        $insert = $y.IndexOf("slashCommands:")
        $y = $y.Substring(0, $insert) + $newYaml + $y.Substring($insert)
        Set-Content $paths.Continue -Value $y -Encoding UTF8
        Write-Output "[UPDATED] Continue — added mcpServers block"
    }
}

# 4. VS Code user
if ($WhatIf) { Write-Output "[WHATIF] Would update $($paths.VSCode)" }
else {
    $v = Get-Content $paths.VSCode -Raw | ConvertFrom-Json
    if ($v.servers.$ServerName) {
        Write-Output "[EXISTS] VS Code — $ServerName already present"
    } else {
        $entry = @{ type = "stdio"; command = "npx"; args = @("-y", $Package, "--isolated") }
        $v.servers | Add-Member -MemberType NoteProperty -Name $ServerName -Value $entry -Force
        $v | ConvertTo-Json -Depth 5 | Set-Content $paths.VSCode -Encoding UTF8
        Write-Output "[UPDATED] VS Code — added $ServerName"
    }
}

Write-Output "`n=== Complete ==="
Write-Output "Backup directory: $bkDir"
if (-not $WhatIf) {
    Write-Output "Run .\verify-global-playwright-mcp.ps1 to validate."
}
