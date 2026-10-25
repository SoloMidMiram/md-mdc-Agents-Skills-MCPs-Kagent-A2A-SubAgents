BeforeAll {
    $SkillNamePattern = "(?m)^name:\s*{0}\r?$"
    $ManualSkillPattern = "(?m)^disable-model-invocation:\s*true\r?$"
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    $ReviewSkillRoot = Join-Path $RepoRoot ".agents\skills\review-kagent-capability"
    $SyncSkillRoot = Join-Path $RepoRoot ".agents\skills\sync-educational-slice"
    $ReviewValidator = Join-Path $ReviewSkillRoot "scripts\validate-review.ps1"
    $SliceAudit = Join-Path $SyncSkillRoot "scripts\audit-slice.ps1"

    function New-ReviewFixture {
        param(
            [Parameter(Mandatory = $true)][string]$Path,
            [int]$ClaimsChecked = 1
        )
        [pscustomobject]@{
            schemaVersion = "1.0"
            review = [pscustomobject]@{
                scope = "evidence/kagent/example.md"
                observedAt = "2026-07-23T00:00:00Z"
                claims = @(
                    [pscustomobject]@{
                        level = "L6"
                        claim = "Agent-mediated MCP execution is proven."
                        classification = "Not proven"
                        sources = @("evidence/kagent/example.md#observation")
                        rationale = "No correlated same-task tool observation exists."
                        promotionCriteriaChecked = $true
                    }
                )
                hardFindings = @()
                softObservations = @()
                verdict = [pscustomobject]@{
                    claimsChecked = $ClaimsChecked
                    proven = 0
                    notProven = 1
                    blocked = 0
                    notAttempted = 0
                    currentStatusChanged = $false
                    summary = "L6 remains Not proven."
                }
            }
        } | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding utf8
    }
}

Describe "Agent-governance skill contracts" {
    It "validates exact skill metadata for <Case> with <Ending>" -TestCases @(
        foreach ($ending in @("LF", "CRLF")) {
            $newline = if ($ending -eq "LF") { "`n" } else { "`r`n" }
            foreach ($name in @("review-kagent-capability", "sync-educational-slice")) {
                foreach ($case in @(
                    @{ Case = "valid"; NameLine = "name: $name"; FlagLine = "disable-model-invocation: true"; Expected = $true },
                    @{ Case = "wrong name"; NameLine = "name: other"; FlagLine = "disable-model-invocation: true"; Expected = $false },
                    @{ Case = "missing name"; NameLine = "description: absent"; FlagLine = "disable-model-invocation: true"; Expected = $false },
                    @{ Case = "name suffix"; NameLine = "name: $name-extra"; FlagLine = "disable-model-invocation: true"; Expected = $false },
                    @{ Case = "false flag"; NameLine = "name: $name"; FlagLine = "disable-model-invocation: false"; Expected = $false },
                    @{ Case = "missing flag"; NameLine = "name: $name"; FlagLine = "description: absent"; Expected = $false },
                    @{ Case = "flag suffix"; NameLine = "name: $name"; FlagLine = "disable-model-invocation: true-extra"; Expected = $false }
                )) {
                    @{ Case = "$name $($case.Case)"; Ending = $ending; SkillName = $name;
                        Raw = "---$newline$($case.NameLine)$newline$($case.FlagLine)$newline---$newline";
                        Expected = $case.Expected }
                }
            }
        }
    ) {
        param($Raw, $SkillName, $Expected)
        $accepted = ($Raw -match ($SkillNamePattern -f [regex]::Escape($SkillName))) -and
            ($Raw -match $ManualSkillPattern)
        $accepted | Should -Be $Expected
    }

    It "uses Cursor-supported manual-only project skill metadata" {
        foreach ($skillRoot in @($ReviewSkillRoot, $SyncSkillRoot)) {
            $skillPath = Join-Path $skillRoot "SKILL.md"
            $raw = Get-Content -Raw -LiteralPath $skillPath
            $raw | Should -Match $ManualSkillPattern
            $name = [IO.Path]::GetFileName($skillRoot)
            $raw | Should -Match ($SkillNamePattern -f [regex]::Escape($name))
            (Join-Path $skillRoot "scripts") | Should -Exist
        }
    }

    It "accepts a structurally consistent capability review" {
        $fixture = Join-Path $TestDrive "valid-review.json"
        New-ReviewFixture -Path $fixture

        $output = & $ReviewValidator -Path $fixture
        $LASTEXITCODE | Should -Be 0
        ($output | ConvertFrom-Json).valid | Should -BeTrue
    }

    It "rejects contradictory capability-review counts" {
        $fixture = Join-Path $TestDrive "invalid-review.json"
        New-ReviewFixture -Path $fixture -ClaimsChecked 2

        $null = & $ReviewValidator -Path $fixture 2>$null
        $LASTEXITCODE | Should -Be 2
    }

    It "audits a clean minimal repository deterministically" {
        $root = Join-Path $TestDrive "clean-repo"
        New-Item -ItemType Directory -Path $root | Out-Null
        "# Test" | Set-Content -LiteralPath (Join-Path $root "README.md") -Encoding utf8
        @"
entries:
  - path: README.md
    purpose: entry
    status: stable
    authority: true
"@ | Set-Content -LiteralPath (Join-Path $root "REPO_MANIFEST.yaml") -Encoding utf8
        git -C $root init --quiet

        $output = & $SliceAudit -RepoRoot $root -RequireEmptyStaging
        $LASTEXITCODE | Should -Be 0
        ($output | ConvertFrom-Json).passed | Should -BeTrue
    }

    It "fails the slice audit on duplicate manifest mappings" {
        $root = Join-Path $TestDrive "duplicate-repo"
        New-Item -ItemType Directory -Path $root | Out-Null
        "# Test" | Set-Content -LiteralPath (Join-Path $root "README.md") -Encoding utf8
        @"
entries:
  - path: README.md
  - path: README.md
"@ | Set-Content -LiteralPath (Join-Path $root "REPO_MANIFEST.yaml") -Encoding utf8
        git -C $root init --quiet

        $output = & $SliceAudit -RepoRoot $root -RequireEmptyStaging
        $LASTEXITCODE | Should -Be 1
        ($output | ConvertFrom-Json).manifest.duplicates | Should -Contain "README.md"
    }

    It "parses every bundled PowerShell helper without errors" {
        foreach ($path in @($ReviewValidator, $SliceAudit)) {
            $tokens = $null
            $errors = $null
            [Management.Automation.Language.Parser]::ParseFile(
                $path,
                [ref]$tokens,
                [ref]$errors
            ) | Out-Null
            @($errors).Count | Should -Be 0
        }
    }
}
