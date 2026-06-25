<#
.SYNOPSIS
    Infrastructure evaluation tests for playwright-global MCP.
.DESCRIPTION
    Tests config format parsing, backup/restore round-trips, entry comparison,
    and duplicate detection. Does not require the actual host editors to be open.
#>

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot "test-helper.psm1"
    Import-Module $modulePath -Force
    $Script:FixtureDir = Join-Path $PSScriptRoot "fixtures"
}

Describe "Config Format Parsing" -Tag "Infrastructure", "Parsing" {

    It "Parses Cursor JSON fixture correctly" {
        $path = Join-Path $Script:FixtureDir "cursor-mcp-fixture.json"
        $entry = Get-NormalizedEntry -Path $path -Format "JSON" -ServerKey "mcpServers"
        $entry | Should -Not -BeNullOrEmpty
        Test-EntryMatches $entry | Should -Be $true
    }

    It "Parses VS Code JSON fixture correctly" {
        $path = Join-Path $Script:FixtureDir "vscode-mcp-fixture.json"
        $entry = Get-NormalizedEntry -Path $path -Format "JSON" -ServerKey "servers"
        $entry | Should -Not -BeNullOrEmpty
        Test-EntryMatches -Actual $entry -ExpectedType "stdio" | Should -Be $true
    }

    It "Parses Codex TOML fixture correctly" {
        $path = Join-Path $Script:FixtureDir "codex-config-fixture.toml"
        $entry = Get-NormalizedEntry -Path $path -Format "TOML"
        $entry | Should -Not -BeNullOrEmpty
        Test-EntryMatches $entry | Should -Be $true
    }

    It "Parses Continue YAML fixture correctly" {
        $path = Join-Path $Script:FixtureDir "continue-config-fixture.yaml"
        $entry = Get-NormalizedEntry -Path $path -Format "YAML"
        $entry | Should -Not -BeNullOrEmpty
        Test-EntryMatches -Actual $entry -ExpectedType "stdio" | Should -Be $true
    }

    It "Returns null for missing playwright-global entry" {
        $tmp = [System.IO.Path]::GetTempFileName()
        try {
            '{"mcpServers":{"other-server":{"command":"x"}}}' | Set-Content $tmp -Encoding UTF8
            $entry = Get-NormalizedEntry -Path $tmp -Format "JSON" -ServerKey "mcpServers"
            $entry | Should -BeNullOrEmpty
        } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    }

    It "Returns null for non-existent file" {
        $entry = Get-NormalizedEntry -Path "Z:\nonexistent\file.json" -Format "JSON"
        $entry | Should -BeNullOrEmpty
    }

    It "Returns null for malformed JSON" {
        $tmp = [System.IO.Path]::GetTempFileName()
        try {
            'not-json' | Set-Content $tmp -Encoding UTF8
            $entry = Get-NormalizedEntry -Path $tmp -Format "JSON" -ServerKey "mcpServers"
            $entry | Should -BeNullOrEmpty
        } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    }
}

Describe "Entry Comparison" -Tag "Infrastructure", "Comparison" {

    It "Detects matching entries" {
        $actual = @{ command = "npx"; args = @("-y", "@playwright/mcp@0.0.76", "--isolated"); type = $null }
        Test-EntryMatches $actual | Should -Be $true
    }

    It "Detects mismatched command" {
        $actual = @{ command = "npm"; args = @("-y", "@playwright/mcp@0.0.76", "--isolated"); type = $null }
        Test-EntryMatches $actual | Should -Be $false
    }

    It "Detects mismatched args" {
        $actual = @{ command = "npx"; args = @("@playwright/mcp@0.0.76"); type = $null }
        Test-EntryMatches $actual | Should -Be $false
    }

    It "Detects mismatched type" {
        $actual = @{ command = "npx"; args = @("-y", "@playwright/mcp@0.0.76", "--isolated"); type = "http" }
        Test-EntryMatches -Actual $actual -ExpectedType "stdio" | Should -Be $false
    }

    It "Handles null actual gracefully" {
        Test-EntryMatches $null | Should -Be $false
    }

    It "Handles empty args correctly" {
        $actual = @{ command = "npx"; args = @(); type = $null }
        Test-EntryMatches $actual | Should -Be $false
    }
}

Describe "Backup-Restore Round-Trip" -Tag "Infrastructure", "RoundTrip" {

    It "Performs byte-for-byte backup and restore" {
        $workspace = New-TestWorkspace
        try {
            Deploy-Fixtures $workspace

            # Build file map
            $fileMap = @(
                @{ Source = Join-Path $workspace ".cursor\mcp.json";       BackupName = "cursor-mcp.json" }
                @{ Source = Join-Path $workspace ".codex\config.toml";     BackupName = "codex-config.toml" }
                @{ Source = Join-Path $workspace ".continue\config.yaml";  BackupName = "continue-config.yaml" }
                @{ Source = Join-Path $workspace "Code\User\mcp.json";     BackupName = "vscode-user-mcp.json" }
            )

            # Capture pre-backup hashes
            $preHashes = Get-FileHashSet -Paths ($fileMap | ForEach-Object { $_.Source })

            # Backup
            $bkDir = New-BackupDir -Root (Join-Path $workspace ".backups")
            Backup-Files -BackupDir $bkDir -FileMap $fileMap

            # Verify backup manifest created
            Join-Path $bkDir "manifest-sha256.txt" | Should -Exist

            # Corrupt originals to prove restore works
            foreach ($item in $fileMap) {
                "CORRUPTED" | Set-Content $item.Source -Encoding UTF8 -Force
            }

            # Restore
            Restore-Files -BackupDir $bkDir -FileMap $fileMap

            # Verify byte-for-byte equality
            $postHashes = Get-FileHashSet -Paths ($fileMap | ForEach-Object { $_.Source })
            $preHashes.Count | Should -Be $postHashes.Count
            foreach ($key in $preHashes.Keys) {
                $postHashes[$key] | Should -Be $preHashes[$key]
            }

            # Verify manifest entries
            $manifest = Get-Content (Join-Path $bkDir "manifest-sha256.txt")
            $manifest.Count | Should -Be 4
        } finally { Remove-TestWorkspace }
    }

    It "Does not fail when source file is missing" {
        $workspace = New-TestWorkspace
        try {
            $fileMap = @(
                @{ Source = Join-Path $workspace "nonexistent.json"; BackupName = "nonexistent.json" }
            )
            $bkDir = New-BackupDir -Root (Join-Path $workspace ".backups")
            # Should not throw
            { Backup-Files -BackupDir $bkDir -FileMap $fileMap } | Should -Not -Throw
        } finally { Remove-TestWorkspace }
    }

    It "BackupDir creates timestamped directory" {
        $workspace = New-TestWorkspace
        try {
            $bkDir = New-BackupDir -Root (Join-Path $workspace ".backups")
            $bkDir | Should -Exist
            $bkDir | Should -Match '\d{8}-\d{6}$'
        } finally { Remove-TestWorkspace }
    }
}

Describe "Host Availability" -Tag "Infrastructure", "Hosts" {

    It "Host 'node' is available" {
        [bool](Get-Command "node" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Host 'npm' is available" {
        [bool](Get-Command "npm" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Host 'npx' is available" {
        [bool](Get-Command "npx" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Host 'python' is available" {
        [bool](Get-Command "python" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Host 'codex' is available" {
        [bool](Get-Command "codex" -ErrorAction SilentlyContinue) | Should -Be $true
    }

    It "Host 'code' is available (optional)" -Skip:$true { $true | Should -Be $true }
    It "Host 'cursor' is available (optional)" -Skip:$true { $true | Should -Be $true }
}

Describe "Package Availability" -Tag "Infrastructure", "Package" {

    It "Playwright MCP package is installable" {
        $out = npx -y "@playwright/mcp@0.0.76" --help 2>&1 | Out-String
        $out | Should -Match "Usage:"
    }
}

Describe "Workspace Duplicate Detection" -Tag "Infrastructure", "Duplicates" {

    It "Detects no workspace-level MCP configs in this repo" {
        $repoRoot = Split-Path -Path $PSScriptRoot -Parent
        $duplicates = @(
            @{ Path = Join-Path $repoRoot ".vscode\mcp.json";        Condition = { param($c) $c -match "playwright" } }
            @{ Path = Join-Path $repoRoot ".continue\mcpServers";    Condition = { param($c) Test-Path $c } }
            @{ Path = Join-Path $repoRoot ".codex\config.toml";      Condition = { param($c) Test-Path $c } }
        )
        $issues = @()
        foreach ($d in $duplicates) {
            if (Test-Path $d.Path) {
                $content = Get-Content $d.Path -Raw -ErrorAction SilentlyContinue
                $cond = & $d.Condition $content
                if ($cond) { $issues += $d.Path }
            }
        }
        $issues | Should -BeNullOrEmpty -Because "workspace-level playwright entries should have been removed"
    }
}

Describe "Fixture Integrity" -Tag "Infrastructure", "Fixtures" {

    It "All fixture files exist" {
        @("cursor-mcp-fixture.json", "codex-config-fixture.toml", "continue-config-fixture.yaml", "vscode-mcp-fixture.json") | ForEach-Object {
            Join-Path $Script:FixtureDir $_ | Should -Exist
        }
    }

    It "Fixture JSON files are valid JSON" {
        @("cursor-mcp-fixture.json", "vscode-mcp-fixture.json") | ForEach-Object {
            $path = Join-Path $Script:FixtureDir $_
            { Get-Content $path -Raw | ConvertFrom-Json } | Should -Not -Throw
        }
    }

    It "Fixture TOML file has playwright-global section" {
        $path = Join-Path $Script:FixtureDir "codex-config-fixture.toml"
        $content = Get-Content $path -Raw
        $content | Should -Match '\[mcp_servers\.playwright-global\]'
    }

    It "Fixture YAML file has playwright-global entry" {
        $path = Join-Path $Script:FixtureDir "continue-config-fixture.yaml"
        $content = Get-Content $path -Raw
        $content | Should -Match 'name: playwright-global'
    }
}
