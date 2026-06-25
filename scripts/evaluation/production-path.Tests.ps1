<#
.SYNOPSIS
    Production-path tests that execute the real installer, verifier, and rollback
    scripts against temporary targets via -ConfigRoot.
.DESCRIPTION
    These tests call the actual production scripts, not helper functions,
    proving that the end-to-end install → verify → rollback round-trip works.
#>

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot "test-helper.psm1"
    Import-Module $modulePath -Force
    $Script:FixtureDir    = Join-Path $PSScriptRoot "fixtures"
    $Script:InstallScript  = Join-Path (Split-Path $PSScriptRoot -Parent) "install-global-playwright-mcp.ps1"
    $Script:VerifyScript   = Join-Path (Split-Path $PSScriptRoot -Parent) "verify-global-playwright-mcp.ps1"
    $Script:RollbackScript = Join-Path (Split-Path $PSScriptRoot -Parent) "rollback-global-playwright-mcp.ps1"
    $Script:ServerName     = "playwright-global"
}

Describe "Production Path: Install Create" -Tag "ProductionPath", "Install" {

    It "Creates entry from scratch in JSON target" {
        $workspace = New-TestWorkspace
        try {
            # Create a Cursor mcp.json with mcpServers present but empty
            $cursorDir = Join-Path $workspace ".cursor"
            New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
            '{"mcpServers":{}}' | Set-Content (Join-Path $cursorDir "mcp.json") -Encoding UTF8

            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

            $result = & $Script:InstallScript -ConfigRoot $workspace 2>&1
            $exitCode = $LASTEXITCODE
            $result -join "`n" | Should -Match "CREATE.*(Cursor|Codex|Continue|VS Code)"

            # Verify cursor entry was created
            $cursorContent = Get-Content (Join-Path $cursorDir "mcp.json") -Raw | ConvertFrom-Json
            $cursorContent.mcpServers.$Script:ServerName.command | Should -Be "npx"
        } finally { Remove-TestWorkspace }
    }

    It "Creates entry when server container key is absent (JSON)" {
        $workspace = New-TestWorkspace
        try {
            $cursorDir = Join-Path $workspace ".cursor"
            New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
            # No mcpServers key at all
            '{"other-key":"value"}' | Set-Content (Join-Path $cursorDir "mcp.json") -Encoding UTF8

            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

            & $Script:InstallScript -ConfigRoot $workspace 2>&1 | Out-Null

            $cursorContent = Get-Content (Join-Path $cursorDir "mcp.json") -Raw | ConvertFrom-Json
            $cursorContent.mcpServers.$Script:ServerName.command | Should -Be "npx"
        } finally { Remove-TestWorkspace }
    }

    It "Creates entry when server key exists but playwright-global is absent (JSON)" {
        $workspace = New-TestWorkspace
        try {
            $cursorDir = Join-Path $workspace ".cursor"
            New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
            '{"mcpServers":{"other-server":{"command":"x"}}}' | Set-Content (Join-Path $cursorDir "mcp.json") -Encoding UTF8

            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

            & $Script:InstallScript -ConfigRoot $workspace 2>&1 | Out-Null

            $cursorContent = Get-Content (Join-Path $cursorDir "mcp.json") -Raw | ConvertFrom-Json
            $cursorContent.mcpServers.$Script:ServerName.command | Should -Be "npx"
            $cursorContent.mcpServers."other-server".command | Should -Be "x"
        } finally { Remove-TestWorkspace }
    }

    It "Creates entry in YAML with trailing sections preserved" {
        $workspace = New-TestWorkspace
        try {
            $continueDir = Join-Path $workspace ".continue"
            New-Item -ItemType Directory -Path $continueDir -Force | Out-Null
            # YAML with mcpServers present but no playwright-global, plus trailing sections
            $yaml = @"
models:
  - title: Test Model
    provider: openai
    model: gpt-4

mcpServers:
  - name: other-server
    type: stdio
    command: custom

slashCommands:
  - name: test
    description: Test command
"@
            Set-Content (Join-Path $continueDir "config.yaml") -Value $yaml -Encoding UTF8

            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

            & $Script:InstallScript -ConfigRoot $workspace 2>&1 | Out-Null

            $updated = Get-Content (Join-Path $continueDir "config.yaml") -Raw
            $updated | Should -Match "name: playwright-global"
            $updated | Should -Match "slashCommands:"
            $updated | Should -Match "name: test"
            $updated | Should -Match "models:"
            $updated | Should -Match "Test Model"
        } finally { Remove-TestWorkspace }
    }
}

Describe "Production Path: Install Idempotence" -Tag "ProductionPath", "Idempotent" {

    It "Second run with correct entries reports no changes" {
        $workspace = New-TestWorkspace
        try {
            Deploy-Fixtures $workspace
            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null
            Copy-Item (Join-Path $workspace "Code\User\mcp.json") (Join-Path $vscodeDir "mcp.json") -Force

            $result = & $Script:InstallScript -ConfigRoot $workspace 2>&1
            $result -join "`n" | Should -Match "EXISTS"
            $result -join "`n" | Should -Not -Match "BACKUP"
        } finally { Remove-TestWorkspace }
    }
}

Describe "Production Path: Malformed File Detection" -Tag "ProductionPath", "Malformed" {

    It "Exits with code 1 on malformed JSON" {
        $workspace = New-TestWorkspace
        try {
            $cursorDir = Join-Path $workspace ".cursor"
            New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
            'not valid json' | Set-Content (Join-Path $cursorDir "mcp.json") -Encoding UTF8

            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

            $result = & $Script:InstallScript -ConfigRoot $workspace 2>&1
            $LASTEXITCODE | Should -Be 1
            $result -join "`n" | Should -Match "MALFORMED"
        } finally { Remove-TestWorkspace }
    }

    It "Does not mutate any files when one is malformed" {
        $workspace = New-TestWorkspace
        try {
            $cursorDir = Join-Path $workspace ".cursor"
            New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
            'not valid json' | Set-Content (Join-Path $cursorDir "mcp.json") -Encoding UTF8

            $codexDir = Join-Path $workspace ".codex"
            New-Item -ItemType Directory -Path $codexDir -Force | Out-Null
            '# empty' | Set-Content (Join-Path $codexDir "config.toml") -Encoding UTF8

            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

            $codexBefore = Get-Content (Join-Path $codexDir "config.toml") -Raw
            & $Script:InstallScript -ConfigRoot $workspace 2>&1 | Out-Null
            $codexAfter = Get-Content (Join-Path $codexDir "config.toml") -Raw
            $codexAfter | Should -Be $codexBefore
        } finally { Remove-TestWorkspace }
    }
}

Describe "Production Path: Verify Exit Codes" -Tag "ProductionPath", "Verify" {

    It "Exits 0 when all entries correct" {
        $workspace = New-TestWorkspace
        try {
            Deploy-Fixtures $workspace
            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null
            Copy-Item (Join-Path $workspace "Code\User\mcp.json") (Join-Path $vscodeDir "mcp.json") -Force

            & $Script:VerifyScript -ConfigRoot $workspace 2>&1 | Out-Null
            $LASTEXITCODE | Should -Be 0
        } finally { Remove-TestWorkspace }
    }

    It "Exits 1 when entry is missing" {
        $workspace = New-TestWorkspace
        try {
            $cursorDir = Join-Path $workspace ".cursor"
            New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
            '{"mcpServers":{}}' | Set-Content (Join-Path $cursorDir "mcp.json") -Encoding UTF8

            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

            & $Script:VerifyScript -ConfigRoot $workspace 2>&1 | Out-Null
            $LASTEXITCODE | Should -Be 1
        } finally { Remove-TestWorkspace }
    }
}

Describe "Production Path: Install → Verify → Rollback Round-Trip" -Tag "ProductionPath", "RoundTrip" {

    It "Completes full round-trip through real production scripts" {
        $workspace = New-TestWorkspace
        try {
            # Deploy fixtures for Codex and Continue only
            $codexDir = Join-Path $workspace ".codex"
            New-Item -ItemType Directory -Path $codexDir -Force | Out-Null
            Copy-Item (Join-Path $Script:FixtureDir "codex-config-fixture.toml") (Join-Path $codexDir "config.toml") -Force

            $continueDir = Join-Path $workspace ".continue"
            New-Item -ItemType Directory -Path $continueDir -Force | Out-Null
            Copy-Item (Join-Path $Script:FixtureDir "continue-config-fixture.yaml") (Join-Path $continueDir "config.yaml") -Force

            # Create Cursor with an empty mcpServers (needs entry created)
            $cursorDir = Join-Path $workspace ".cursor"
            New-Item -ItemType Directory -Path $cursorDir -Force | Out-Null
            '{"mcpServers":{}}' | Set-Content (Join-Path $cursorDir "mcp.json") -Encoding UTF8

            # Create VS Code with an empty servers (needs entry created)
            $vscodeDir = Join-Path $workspace "AppData\Roaming\Code\User"
            New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null
            '{"servers":{}}' | Set-Content (Join-Path $vscodeDir "mcp.json") -Encoding UTF8

            # Capture pre-install hashes
            $preHashes = @{}
            @(
                Join-Path $cursorDir "mcp.json"
                Join-Path $codexDir "config.toml"
                Join-Path $continueDir "config.yaml"
                Join-Path $vscodeDir "mcp.json"
            ) | ForEach-Object {
                if (Test-Path $_) {
                    $preHashes[$_] = (Get-FileHash $_ -Algorithm SHA256).Hash
                }
            }

            # Run installer — should create entries for Cursor + VS Code, skip Codex + Continue (already correct)
            $installResult = & $Script:InstallScript -ConfigRoot $workspace 2>&1
            $LASTEXITCODE | Should -Be 0

            # Get backup dir from output
            $backupLine = ($installResult -join "`n") -split "`n" | Where-Object { $_ -match "Backup directory: " }
            $backupDir = if ($backupLine) { ($backupLine -split ": ", 2)[1].Trim() } else { $null }
            $backupDir | Should -Not -BeNullOrEmpty
            $backupDir | Should -Exist

            # Verify should pass after install
            & $Script:VerifyScript -ConfigRoot $workspace 2>&1 | Out-Null
            $LASTEXITCODE | Should -Be 0

            # Rollback
            & $Script:RollbackScript -BackupDir $backupDir -Force -ConfigRoot $workspace 2>&1
            $LASTEXITCODE | Should -Be 0

            # Verify post-rollback hashes match pre-install
            $postHashes = @{}
            @(
                Join-Path $cursorDir "mcp.json"
                Join-Path $codexDir "config.toml"
                Join-Path $continueDir "config.yaml"
                Join-Path $vscodeDir "mcp.json"
            ) | ForEach-Object {
                if (Test-Path $_) {
                    $postHashes[$_] = (Get-FileHash $_ -Algorithm SHA256).Hash
                }
            }
            # Only Cursor + VS Code were backed up and restored; Codex + Continue unchanged
            foreach ($key in @((Join-Path $cursorDir "mcp.json"), (Join-Path $vscodeDir "mcp.json"))) {
                $postHashes[$key] | Should -Be $preHashes[$key]
            }
        } finally { Remove-TestWorkspace }
    }
}
