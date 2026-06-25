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

    BeforeAll {
        $dataset = Get-EvalDataset
        $structuralEntries = $dataset | Where-Object { $_.group -eq "structural" -and $_.host -ne "workspace" -and $_.host -ne "all" }
        $cliEntries = $dataset | Where-Object { $_.group -eq "functional" -and $_.host -eq "cli" }
    }

    It "Evaluation dataset is non-empty" {
        $dataset | Should -Not -BeNullOrEmpty
        $dataset.Count | Should -BeGreaterThan 0
    }

    It "All dataset entries have required fields" {
        foreach ($item in $dataset) {
            $item.id | Should -Not -BeNullOrEmpty
            $item.group | Should -Not -BeNullOrEmpty
            $item.description | Should -Not -BeNullOrEmpty
            $item.host | Should -Not -BeNullOrEmpty
            $item.expected | Should -Not -BeNullOrEmpty
            $item.severity | Should -BeIn @("critical", "warning", "info")
        }
    }

    It "No duplicate dataset IDs exist" {
        $ids = $dataset | ForEach-Object { $_.id }
        $ids.Count | Should -Be ($ids | Select-Object -Unique).Count
    }

    It "Dataset has entries in each required group" {
        $groups = $dataset | ForEach-Object { $_.group } | Select-Object -Unique
        @("structural", "functional", "backup", "rollback") | ForEach-Object {
            $_ | Should -BeIn $groups
        }
    }

    # Structural checks from dataset: verify each structural entry against real files
    # Uses Get-NormalizedEntry from test-helper to read and parse each config file,
    # then validates the playwright-global entry matches expected metadata.
    # Fails if the file is missing or the entry is absent.

    foreach ($entry in $structuralEntries) {
        It "Dataset structural: $($entry.id) - $($entry.description)" -Tag "DatasetStructural" {
            $hostConfig = switch ($entry.host) {
                "cursor"   { @{ Path = Join-Path $env:USERPROFILE ".cursor\mcp.json";        Format = "JSON";   Key = "mcpServers"; ExpectedType = $null } }
                "vscode"   { @{ Path = Join-Path $env:APPDATA "Code\User\mcp.json";          Format = "JSON";   Key = "servers";     ExpectedType = "stdio" } }
                "codex"    { @{ Path = Join-Path $env:USERPROFILE ".codex\config.toml";      Format = "TOML";   Key = $null;        ExpectedType = $null } }
                "continue" { @{ Path = Join-Path $env:USERPROFILE ".continue\config.yaml";   Format = "YAML";   Key = $null;        ExpectedType = "stdio" } }
            }
            $entry.expected | Should -Not -BeNullOrEmpty
            if ($entry.expected.command) {
                Test-Path $hostConfig.Path | Should -Be $true -Because "config file for $($entry.host) should exist when playwright-global is expected"
                $actualEntry = Get-NormalizedEntry -Path $hostConfig.Path -Format $hostConfig.Format -ServerKey $hostConfig.Key
                $actualEntry | Should -Not -BeNullOrEmpty -Because "$($entry.host) should have a playwright-global entry"
                $actualEntry.command | Should -Be $entry.expected.command
                if ($entry.expected.args) {
                    ($actualEntry.args -join " ") | Should -Be ($entry.expected.args -join " ")
                }
                if ($hostConfig.ExpectedType) {
                    $actualEntry.type | Should -Be $hostConfig.ExpectedType
                }
            }
        }
    }

    # CLI checks from dataset

    It "All dataset CLI entries reference valid commands" -Tag "DatasetFunctional" {
        foreach ($entry in $cliEntries) {
            if ($entry.expected.command_found) {
                Get-Command $entry.expected.command_found -ErrorAction SilentlyContinue | Should -Not -BeNullOrEmpty
            }
        }
    }

    It "Playwright CLI help contains expected output" -Tag "DatasetFunctional" {
        $out = npx -y "@playwright/mcp@0.0.76" --help 2>&1 | Out-String
        $cliEntries | Where-Object { $_.expected.output_contains } | ForEach-Object {
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
