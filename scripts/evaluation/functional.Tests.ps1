<#
.SYNOPSIS
    Functional evaluation tests for playwright-global MCP.
.DESCRIPTION
    Tests real MCP server behavior: package availability, CLI help output,
    and data-driven validation against the JSONL evaluation dataset.
    These tests require network access but do NOT open an editor or browser.
#>

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot "test-helper.psm1"
    Import-Module $modulePath -Force
    $Script:ExpectedCommand = "npx"
    $Script:ExpectedArgs = @("-y", "@playwright/mcp@0.0.76", "--isolated")
    $Script:Package = "@playwright/mcp@0.0.76"
}

Describe "Package Verification" -Tag "Functional", "Package" {

    It "Playwright MCP package version is resolvable" {
        $out = npm view "$Script:Package" version 2>$null
        $out.Trim() | Should -Be "0.0.76"
    }

    It "Playwright MCP CLI responds with help" {
        $out = npx -y "$Script:Package" --help 2>$null | Out-String
        $out | Should -Match "Usage:"
    }

    It "Playwright MCP --isolated flag is documented" {
        $out = npx -y "$Script:Package" --help 2>$null | Out-String
        $out | Should -Match "isolated"
    }
}

Describe "Host Tool Availability" -Tag "Functional", "Hosts" {

    It "Required tool 'node' is on PATH" {
        [bool](Get-Command "node" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Required tool 'npm' is on PATH" {
        [bool](Get-Command "npm" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Required tool 'npx' is on PATH" {
        [bool](Get-Command "npx" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Required tool 'python' is on PATH" {
        [bool](Get-Command "python" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Optional tool 'code' is available" -Skip:$true { $true | Should -Be $true }
    It "Optional tool 'cursor' is available" -Skip:$true { $true | Should -Be $true }
    It "Optional tool 'codex' is available" -Skip:$true { $true | Should -Be $true }
}

Describe "Dataset-Driven Evaluation" -Tag "Functional", "Dataset" {

    BeforeDiscovery {
        $modulePath = Join-Path $PSScriptRoot "test-helper.psm1"
        Import-Module $modulePath -Force
        $script:EvalDataset = Get-EvalDataset
        $script:StructuralEntries = @(
            $script:EvalDataset |
                Where-Object { $_.group -eq "structural" -and $_.host -ne "workspace" -and $_.host -ne "all" }
        )
        $script:StructuralCases = @(
            $script:StructuralEntries | ForEach-Object {
                @{
                    EntryId          = $_.id
                    EntryDescription = $_.description
                    EntryHost        = $_.host
                    EntryExpected    = $_.expected
                }
            }
        )
        $script:CliEntries = @(
            $script:EvalDataset |
                Where-Object { $_.group -eq "functional" -and $_.host -eq "cli" }
        )
    }

    BeforeAll {
        $modulePath = Join-Path $PSScriptRoot "test-helper.psm1"
        Import-Module $modulePath -Force
        $Script:Dataset = Get-EvalDataset
        $Script:CliEntriesRuntime = @(
            $Script:Dataset |
                Where-Object { $_.group -eq "functional" -and $_.host -eq "cli" }
        )

        # Use OS profile folders so assertions stay on the real user even if
        # USERPROFILE/APPDATA env vars are redirected for isolation tests.
        $realUser = [Environment]::GetFolderPath("UserProfile")
        $realAppData = [Environment]::GetFolderPath("ApplicationData")
        $profilePaths = @(
            (Join-Path $realUser ".cursor\mcp.json")
            (Join-Path $realAppData "Code\User\mcp.json")
            (Join-Path $realUser ".codex\config.toml")
            (Join-Path $realUser ".continue\config.yaml")
        )
        $Script:RealProfileBefore = @{}
        foreach ($p in $profilePaths) {
            if (Test-Path -LiteralPath $p) {
                $item = Get-Item -LiteralPath $p
                $Script:RealProfileBefore[$p] = @{
                    Exists = $true
                    Length = [int64]$item.Length
                    Hash   = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
                }
            }
            else {
                $Script:RealProfileBefore[$p] = @{ Exists = $false; Length = $null; Hash = $null }
            }
        }

        $Script:StructuralWorkspace = New-TestWorkspace
        $installer = Join-Path (Split-Path $PSScriptRoot -Parent) "install-global-playwright-mcp.ps1"
        # Run installer in a child pwsh so `exit 1` cannot kill the Pester host.
        try {
            $pwsh = (Get-Command pwsh -ErrorAction Stop).Source
            $preflight = & $pwsh -NoProfile -Command @'
$ErrorActionPreference = "Continue"
Write-Output "preflight: pwsh=$($PSVersionTable.PSVersion)"
Write-Output "preflight: python=$(Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)"
try {
  $ver = & python -c "import yaml; print(yaml.__version__)" 2>&1
  Write-Output "preflight: pyyaml=$ver; exit=$LASTEXITCODE"
} catch {
  Write-Output "preflight: pyyaml_error=$_"
}
'@ 2>&1
            $installOut = & $pwsh -NoProfile -File $installer `
                -ConfigRoot $Script:StructuralWorkspace 2>&1
            $Script:InstallerExitCode = $LASTEXITCODE
            $Script:InstallerOutput = @(($preflight | Out-String), ($installOut | Out-String)) -join "`n"
            $diagDir = Join-Path $PSScriptRoot "results"
            New-Item -ItemType Directory -Force -Path $diagDir | Out-Null
            @(
                "installerExit=$($Script:InstallerExitCode)"
                "workspace=$($Script:StructuralWorkspace)"
                $Script:InstallerOutput
            ) | Set-Content -LiteralPath (Join-Path $diagDir "structural-installer-diag.txt") -Encoding UTF8
        }
        catch {
            $Script:InstallerExitCode = 2
            $Script:InstallerOutput = "$_"
        }
        if ($null -eq $Script:InstallerExitCode) {
            $Script:InstallerExitCode = 1
            $Script:InstallerOutput = "child pwsh returned no exit code`n$($Script:InstallerOutput)"
        }
        if ($Script:InstallerExitCode -ne 0) {
            Write-Warning "Isolated installer failed (exit $($Script:InstallerExitCode)): $($Script:InstallerOutput)"
        }
    }

    AfterAll {
        if ($Script:StructuralWorkspace -and (Test-Path -LiteralPath $Script:StructuralWorkspace)) {
            Remove-Item -LiteralPath $Script:StructuralWorkspace -Recurse -Force -ErrorAction SilentlyContinue
        }
        $Script:StructuralWorkspace = $null
    }

    It "Evaluation dataset is non-empty" {
        $Script:Dataset | Should -Not -BeNullOrEmpty
        $Script:Dataset.Count | Should -BeGreaterThan 0
    }

    It "All dataset entries have required fields" {
        foreach ($item in $Script:Dataset) {
            $item.id | Should -Not -BeNullOrEmpty
            $item.group | Should -Not -BeNullOrEmpty
            $item.description | Should -Not -BeNullOrEmpty
            $item.host | Should -Not -BeNullOrEmpty
            $item.expected | Should -Not -BeNullOrEmpty
            $item.severity | Should -BeIn @("critical", "warning", "info")
        }
    }

    It "No duplicate dataset IDs exist" {
        $ids = $Script:Dataset | ForEach-Object { $_.id }
        $ids.Count | Should -Be ($ids | Select-Object -Unique).Count
    }

    It "Dataset has entries in each required group" {
        $groups = $Script:Dataset | ForEach-Object { $_.group } | Select-Object -Unique
        @("structural", "functional", "backup", "rollback") | ForEach-Object {
            $_ | Should -BeIn $groups
        }
    }

    It "Installer creates isolated configs via -ConfigRoot" -Tag "DatasetStructural" {
        $out = [string]$Script:InstallerOutput
        if ($out.Length -gt 4000) {
            $out = $out.Substring($out.Length - 4000)
        }
        $Script:InstallerExitCode | Should -Be 0 -Because (
            "install-global-playwright-mcp.ps1 -ConfigRoot must succeed for structural proof; " +
            "child exit=$($Script:InstallerExitCode); output tail:`n$out"
        )
        $Script:StructuralWorkspace | Should -Not -BeNullOrEmpty
        Test-Path -LiteralPath $Script:StructuralWorkspace | Should -Be $true
    }

    It "Installer targets stay inside the ConfigRoot workspace" -Tag "DatasetStructural" {
        $workspace = $Script:StructuralWorkspace
        $workspace | Should -Not -BeNullOrEmpty
        $root = [IO.Path]::GetFullPath($workspace)
        if (-not $root.EndsWith([IO.Path]::DirectorySeparatorChar)) {
            $root = $root + [IO.Path]::DirectorySeparatorChar
        }
        $targets = @(
            (Join-Path $workspace ".cursor\mcp.json")
            (Join-Path $workspace "AppData\Roaming\Code\User\mcp.json")
            (Join-Path $workspace ".codex\config.toml")
            (Join-Path $workspace ".continue\config.yaml")
        )
        foreach ($path in $targets) {
            $full = [IO.Path]::GetFullPath($path)
            $full.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) |
                Should -Be $true -Because "resolved path $full must stay under workspace $root"
            Test-Path -LiteralPath $full |
                Should -Be $true -Because "contained installer target must exist: $full"
        }
    }

    It "Dataset structural: <EntryId> - <EntryDescription>" -Tag "DatasetStructural" -ForEach $script:StructuralCases {
        $workspace = $Script:StructuralWorkspace
        $hostConfig = switch ($EntryHost) {
            "cursor" {
                @{
                    Path         = Join-Path $workspace ".cursor\mcp.json"
                    Format       = "JSON"
                    Key          = "mcpServers"
                    ExpectedType = $null
                }
            }
            "vscode" {
                @{
                    Path         = Join-Path $workspace "AppData\Roaming\Code\User\mcp.json"
                    Format       = "JSON"
                    Key          = "servers"
                    ExpectedType = "stdio"
                }
            }
            "codex" {
                @{
                    Path         = Join-Path $workspace ".codex\config.toml"
                    Format       = "TOML"
                    Key          = $null
                    ExpectedType = $null
                }
            }
            "continue" {
                @{
                    Path         = Join-Path $workspace ".continue\config.yaml"
                    Format       = "YAML"
                    Key          = $null
                    ExpectedType = "stdio"
                }
            }
            default {
                throw "Unsupported structural host: $EntryHost"
            }
        }
        $EntryExpected | Should -Not -BeNullOrEmpty
        if ($EntryExpected.command) {
            Test-Path $hostConfig.Path | Should -Be $true -Because "config file for $EntryHost should exist under -ConfigRoot workspace"
            $actualEntry = Get-NormalizedEntry -Path $hostConfig.Path -Format $hostConfig.Format -ServerKey $hostConfig.Key
            $actualEntry | Should -Not -BeNullOrEmpty -Because "$EntryHost should have a playwright-global entry"
            $actualEntry.command | Should -Be $EntryExpected.command
            if ($EntryExpected.args) {
                ($actualEntry.args -join " ") | Should -Be ($EntryExpected.args -join " ")
            }
            if ($hostConfig.ExpectedType) {
                $actualEntry.type | Should -Be $hostConfig.ExpectedType
            }
        }
    }

    It "Real user-profile config files were not created or modified" -Tag "DatasetStructural" {
        $before = $Script:RealProfileBefore
        $before | Should -Not -BeNullOrEmpty
        foreach ($path in $before.Keys) {
            $b = $before[$path]
            if (Test-Path -LiteralPath $path) {
                $item = Get-Item -LiteralPath $path
                $exists = $true
                $length = [int64]$item.Length
                $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
            }
            else {
                $exists = $false
                $length = $null
                $hash = $null
            }
            $exists | Should -Be $b.Exists -Because (
                "secondary safety: existence of $path must be unchanged by -ConfigRoot install " +
                "(can flake if another local app edits this file during the suite)"
            )
            $hash | Should -Be $b.Hash -Because (
                "secondary safety: content of $path must be unchanged by -ConfigRoot install " +
                "(can flake if another local app edits this file during the suite)"
            )
            $length | Should -Be $b.Length -Because (
                "secondary safety: size of $path must be unchanged by -ConfigRoot install " +
                "(can flake if another local app edits this file during the suite)"
            )
        }
    }

    # CLI checks from dataset

    It "All dataset CLI entries reference valid commands" -Tag "DatasetFunctional" {
        foreach ($entry in $Script:CliEntriesRuntime) {
            if ($entry.expected.command_found) {
                Get-Command $entry.expected.command_found -ErrorAction SilentlyContinue | Should -Not -BeNullOrEmpty
            }
        }
    }

    It "Playwright CLI help contains expected output" -Tag "DatasetFunctional" {
        $out = npx -y "@playwright/mcp@0.0.76" --help 2>&1 | Out-String
        $Script:CliEntriesRuntime | Where-Object { $_.expected.output_contains } | ForEach-Object {
            $out | Should -Match $_.expected.output_contains
        }
    }

    It "Dataset backup: backup-001 - Backup dir pattern" -Tag "DatasetFunctional" {
        $workspace = New-TestWorkspace
        try {
            $bkDir = New-BackupDir -Root (Join-Path $workspace ".backups")
            $bkDir | Should -Match '\d{8}-\d{6}$'
        } finally { Remove-TestWorkspace }
    }

    It "Dataset backup: backup-002 - Manifest created" -Tag "DatasetFunctional" {
        $workspace = New-TestWorkspace
        try {
            Deploy-Fixtures $workspace
            $fileMap = @(
                @{ Source = Join-Path $workspace ".cursor\mcp.json"; BackupName = "cursor-mcp.json" }
                @{ Source = Join-Path $workspace ".codex\config.toml"; BackupName = "codex-config.toml" }
            )
            $bkDir = New-BackupDir -Root (Join-Path $workspace ".backups")
            Backup-Files -BackupDir $bkDir -FileMap $fileMap
            Join-Path $bkDir "manifest-sha256.txt" | Should -Exist
        } finally { Remove-TestWorkspace }
    }
}

Describe "Script Integration" -Tag "Functional", "Scripts" {

    It "install-global-playwright-mcp.ps1 loads shared manifest" {
        $path = Join-Path (Split-Path $PSScriptRoot -Parent) "install-global-playwright-mcp.ps1"
        $path | Should -Exist
        $content = Get-Content $path -Raw
        $content | Should -Match 'McpConfigTargets\.ps1'
    }

    It "verify-global-playwright-mcp.ps1 loads shared manifest" {
        $path = Join-Path (Split-Path $PSScriptRoot -Parent) "verify-global-playwright-mcp.ps1"
        $path | Should -Exist
        $content = Get-Content $path -Raw
        $content | Should -Match 'McpConfigTargets\.ps1'
    }

    It "rollback-global-playwright-mcp.ps1 loads shared manifest" {
        $path = Join-Path (Split-Path $PSScriptRoot -Parent) "rollback-global-playwright-mcp.ps1"
        $path | Should -Exist
        $content = Get-Content $path -Raw
        $content | Should -Match 'McpConfigTargets\.ps1'
    }

    It "McpConfigTargets.ps1 defines all 4 config targets" {
        $path = Join-Path (Split-Path $PSScriptRoot -Parent) "McpConfigTargets.ps1"
        $path | Should -Exist
        . $path
        $Script:ConfigTargets.Count | Should -Be 4
        @("Cursor", "Codex", "Continue", "VS Code") | ForEach-Object {
            $Script:ConfigTargets.Name | Should -Contain $_
        }
    }

    It "WhatIf mode does not create backup directory" {
        $path = Join-Path (Split-Path $PSScriptRoot -Parent) "install-global-playwright-mcp.ps1"
        $bkRoot = Join-Path $env:USERPROFILE ".mcp-config-backups"
        $before = if (Test-Path $bkRoot) { (Get-ChildItem $bkRoot).Count } else { 0 }
        & $path -WhatIf 2>&1 | Out-Null
        $after = if (Test-Path $bkRoot) { (Get-ChildItem $bkRoot).Count } else { 0 }
        $after | Should -Be $before -Because "-WhatIf must not create backups"
    }
}
