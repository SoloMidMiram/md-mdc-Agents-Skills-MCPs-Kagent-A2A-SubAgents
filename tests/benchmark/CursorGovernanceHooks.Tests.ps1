BeforeAll {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    $ModulePath = Join-Path $RepoRoot ".cursor\hooks\GovernanceHooks.psm1"
    $ScriptPath = Join-Path $RepoRoot ".cursor\hooks\governance-hook.ps1"
    $ConfigPath = Join-Path $RepoRoot ".cursor\hooks.json"
    Import-Module $ModulePath -Force
}

Describe "Cursor governance hook contract" {
    It "registers all three shadow hook events with bounded timeouts" {
        $config = Get-Content -Raw $ConfigPath | ConvertFrom-Json
        $config.version | Should -Be 1
        foreach ($eventName in @("afterFileEdit", "beforeShellExecution", "stop")) {
            $hook = @($config.hooks.$eventName)
            $hook.Count | Should -Be 1
            $hook[0].command | Should -Match "governance-hook\.ps1"
            $hook[0].command | Should -Match "-EventName $eventName"
            $hook[0].timeout | Should -BeLessOrEqual 10
        }
    }

    It "maps edited files to deterministic validation families" {
        $requirements = Get-GovernanceRequirements `
            -RelativePath "tests/benchmark/CursorGovernanceHooks.Tests.ps1"
        $requirements | Should -Contain "powershell-parser"
        $requirements | Should -Contain "pester"
        $requirements | Should -Contain "governance-benchmark"
        $requirements | Should -Contain "governance-contract"
    }

    It "does not retain an absolute path outside the repository" {
        $path = ConvertTo-GovernancePath `
            -Path "C:\Users\example\secret.txt" `
            -RepoRoot $RepoRoot
        $path | Should -Be "outside-workspace"
    }

    It "classifies high-risk commands without storing their raw text" {
        $logRoot = Join-Path $TestDrive "risk-log"
        $inputObject = [pscustomobject]@{
            conversation_id = "session-risk"
            command = "git add .; kubectl delete pod private-name"
        }
        $result = Invoke-GovernanceHook `
            -EventName beforeShellExecution `
            -InputObject $inputObject `
            -RepoRoot $RepoRoot `
            -LogRoot $logRoot

        $result.record.riskSignals | Should -Contain "broad-staging"
        $result.record.riskSignals | Should -Contain "live-mutation"
        $result.record.blocked | Should -BeFalse
        $log = Get-Content -Raw (Join-Path $logRoot "events.jsonl")
        $log | Should -Not -Match "private-name"
        $log | Should -Not -Match "git add"
        $log | Should -Not -Match "session-risk"
    }

    It "does not flag read-only Git and Kubernetes commands as risky" {
        $result = Get-GovernanceShellObservation `
            -Command "git status --short; kubectl get pods -n kagent"

        @($result.risks).Count | Should -Be 0
    }

    It "tracks required and observed validation by hashed session" {
        $logRoot = Join-Path $TestDrive "state-log"
        $edit = [pscustomobject]@{
            conversation_id = "session-state"
            file_path = "tests/benchmark/CursorGovernanceHooks.Tests.ps1"
        }
        $null = Invoke-GovernanceHook `
            -EventName afterFileEdit `
            -InputObject $edit `
            -RepoRoot $RepoRoot `
            -LogRoot $logRoot
        $shell = [pscustomobject]@{
            conversation_id = "session-state"
            command = "Invoke-Pester tests/benchmark/CursorGovernanceHooks.Tests.ps1"
        }
        $null = Invoke-GovernanceHook `
            -EventName beforeShellExecution `
            -InputObject $shell `
            -RepoRoot $RepoRoot `
            -LogRoot $logRoot
        $stop = Invoke-GovernanceHook `
            -EventName stop `
            -InputObject ([pscustomobject]@{ conversation_id = "session-state" }) `
            -RepoRoot $RepoRoot `
            -LogRoot $logRoot

        $stop.record.missingValidations | Should -Contain "powershell-parser"
        $stop.record.missingValidations | Should -Not -Contain "pester"
        $stop.record.missingValidations | Should -Not -Contain "governance-contract"
        $stop.record.missingValidations | Should -Not -Contain "governance-benchmark"
        (Get-ChildItem (Join-Path $logRoot "sessions") -Filter "*.json").Count |
            Should -Be 1
    }

    It "fails open with valid JSON when input is malformed" {
        $logRoot = Join-Path $TestDrive "malformed-log"
        $output = "not-json" | & $ScriptPath `
            -EventName beforeShellExecution `
            -RepoRoot $RepoRoot `
            -LogRoot $logRoot

        $LASTEXITCODE | Should -Be 0
        { $output | ConvertFrom-Json } | Should -Not -Throw
        @(($output | ConvertFrom-Json).PSObject.Properties).Count | Should -Be 0
    }

    It "fails open when the hook module is unavailable" {
        $isolatedRoot = Join-Path $TestDrive "isolated"
        New-Item -ItemType Directory -Path $isolatedRoot | Out-Null
        $isolatedScript = Join-Path $isolatedRoot "governance-hook.ps1"
        Copy-Item -LiteralPath $ScriptPath -Destination $isolatedScript

        $output = '{}' | & $isolatedScript `
            -EventName afterFileEdit `
            -RepoRoot $RepoRoot `
            -LogRoot (Join-Path $TestDrive "missing-module-log")

        $LASTEXITCODE | Should -Be 0
        { $output | ConvertFrom-Json } | Should -Not -Throw
    }

    It "completes a normal observation within the configured timeout" {
        $elapsed = Measure-Command {
            $null = '{}' | & $ScriptPath `
                -EventName stop `
                -RepoRoot $RepoRoot `
                -LogRoot (Join-Path $TestDrive "latency-log")
        }

        $LASTEXITCODE | Should -Be 0
        $elapsed.TotalSeconds | Should -BeLessThan 10
    }

    It "does not return a blocking or automatic follow-up field" {
        $logRoot = Join-Path $TestDrive "output-log"
        $output = '{}' | & $ScriptPath `
            -EventName stop `
            -RepoRoot $RepoRoot `
            -LogRoot $logRoot
        $result = $output | ConvertFrom-Json

        $LASTEXITCODE | Should -Be 0
        $result.PSObject.Properties.Name | Should -Not -Contain "permission"
        $result.PSObject.Properties.Name | Should -Not -Contain "followup_message"
    }
}
