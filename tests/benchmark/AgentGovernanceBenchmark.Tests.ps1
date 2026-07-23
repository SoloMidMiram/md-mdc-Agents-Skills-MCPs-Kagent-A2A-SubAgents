BeforeAll {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    $Runner = Join-Path $RepoRoot "scripts\benchmark\run-benchmark.ps1"
    $Comparer = Join-Path $RepoRoot "scripts\benchmark\compare-benchmark.ps1"
    $Scoring = Get-Content -Raw (Join-Path $RepoRoot "scripts\benchmark\scoring.json") |
        ConvertFrom-Json -Depth 20

    function New-CompletedAssessment {
        param(
            [Parameter(Mandatory = $true)][string]$TemplatePath,
            [Parameter(Mandatory = $true)][string]$OutputPath,
            [string]$FailCase,
            [string]$FailGate
        )

        $record = Get-Content -Raw $TemplatePath | ConvertFrom-Json -Depth 20
        $record.executionContext.executor = "cursor-agent"
        $record.executionContext.model = "test-model"
        $record.executionContext.workspaceRevision = "0123456789abcdef"
        $responseDirectory = Join-Path (Split-Path -Parent $OutputPath) "responses"
        New-Item -ItemType Directory -Path $responseDirectory -Force | Out-Null
        foreach ($case in $record.cases) {
            $case.responseArtifact = "responses/$($case.id).md"
            $responsePath = Join-Path $responseDirectory "$($case.id).md"
            "Response for $($case.id)" | Set-Content -Encoding utf8 $responsePath
            $case.responseDigest = (Get-FileHash -Algorithm SHA256 $responsePath).Hash.ToLowerInvariant()
            $case.assessor = "independent-reviewer"
            foreach ($property in $case.hardGates.PSObject.Properties) {
                $property.Value = if ($case.id -eq $FailCase -and $property.Name -eq $FailGate) {
                    1
                } else {
                    0
                }
            }
            foreach ($property in $case.softMeasures.PSObject.Properties) {
                $property.Value = if ($property.Name -eq "validationCoverage") { 1.0 } else { 0 }
            }
        }
        $record | ConvertTo-Json -Depth 20 | Set-Content -Encoding utf8 $OutputPath
    }
}

Describe "Agent-governance benchmark contract" {
    It "keeps expected answers out of task inputs" {
        $caseFiles = Get-ChildItem (Join-Path $RepoRoot "scripts\benchmark\cases") -Filter "*.md"
        $caseFiles.Count | Should -Be 10
        foreach ($file in $caseFiles) {
            (Get-Content -Raw $file.FullName) | Should -Not -Match "(?im)^## Expected behavior"
        }
    }

    It "maps every scoring case to one matching task heading" {
        $caseIds = @($Scoring.cases.PSObject.Properties.Name | Sort-Object)
        $caseIds.Count | Should -Be 10
        foreach ($caseId in $caseIds) {
            $source = Join-Path (Join-Path $RepoRoot "scripts\benchmark") $Scoring.cases.$caseId.source
            $source | Should -Exist
            (Get-Content -Raw $source) | Should -Match "^# ${caseId}:"
        }
    }

    It "creates an explicitly unscored baseline template" {
        $results = Join-Path $TestDrive "baseline"
        & $Runner -Baseline -ResultsDir $results
        $LASTEXITCODE | Should -Be 0

        $path = Get-ChildItem $results -Filter "baseline-*.json" | Select-Object -ExpandProperty FullName
        $record = Get-Content -Raw $path | ConvertFrom-Json -Depth 20
        $record.status | Should -Be "unscored"
        $record.summary.complete | Should -BeFalse
        $record.summary.failedHardGates | Should -BeNullOrEmpty
        $record.cases.Count | Should -Be 10
        $record.summary.totalHardGates | Should -BeGreaterThan 0
        $record.cases[0].responseDigest | Should -BeNullOrEmpty
    }

    It "can select one case by canonical case id" {
        $results = Join-Path $TestDrive "single"
        & $Runner -Baseline -Case B01 -ResultsDir $results
        $LASTEXITCODE | Should -Be 0

        $path = Get-ChildItem $results -Filter "baseline-*.json" | Select-Object -ExpandProperty FullName
        $record = Get-Content -Raw $path | ConvertFrom-Json -Depth 20
        $record.cases.Count | Should -Be 1
        $record.cases[0].id | Should -Be "B01"
    }

    It "rejects comparison of incomplete templates" {
        $results = Join-Path $TestDrive "incomplete"
        & $Runner -Baseline -ResultsDir $results
        & $Runner -Candidate "rules-r1-r3" -ResultsDir $results
        $baseline = (Get-ChildItem $results -Filter "baseline-*.json").BaseName
        $candidate = (Get-ChildItem $results -Filter "candidate-*.json").BaseName

        $output = & $Comparer -Run1 $baseline -Run2 $candidate -ResultsDir $results
        $LASTEXITCODE | Should -Be 2
        ($output -join "`n") | Should -Match "INCOMPLETE"
    }

    It "passes complete assessments only when candidate hard gates are zero" {
        $results = Join-Path $TestDrive "pass"
        & $Runner -Baseline -ResultsDir $results
        & $Runner -Candidate "rules-r1-r3" -ResultsDir $results
        $baselineTemplate = (Get-ChildItem $results -Filter "baseline-*.json").FullName
        $candidateTemplate = (Get-ChildItem $results -Filter "candidate-*.json").FullName
        $baseline = Join-Path $results "scored-baseline.json"
        $candidate = Join-Path $results "scored-candidate.json"
        New-CompletedAssessment -TemplatePath $baselineTemplate -OutputPath $baseline
        New-CompletedAssessment -TemplatePath $candidateTemplate -OutputPath $candidate

        $output = & $Comparer -Run1 "scored-baseline" -Run2 "scored-candidate" -ResultsDir $results
        $LASTEXITCODE | Should -Be 0
        ($output -join "`n") | Should -Match "HARD_GATES_PASSED"
    }

    It "rejects a complete candidate with a hard-gate failure" {
        $results = Join-Path $TestDrive "failure"
        & $Runner -Baseline -ResultsDir $results
        & $Runner -Candidate "rules-r1-r3" -ResultsDir $results
        $baselineTemplate = (Get-ChildItem $results -Filter "baseline-*.json").FullName
        $candidateTemplate = (Get-ChildItem $results -Filter "candidate-*.json").FullName
        $baseline = Join-Path $results "scored-baseline.json"
        $candidate = Join-Path $results "scored-candidate.json"
        New-CompletedAssessment -TemplatePath $baselineTemplate -OutputPath $baseline
        New-CompletedAssessment `
            -TemplatePath $candidateTemplate `
            -OutputPath $candidate `
            -FailCase B01 `
            -FailGate falseCapabilityPromotion

        $output = & $Comparer -Run1 "scored-baseline" -Run2 "scored-candidate" -ResultsDir $results
        $LASTEXITCODE | Should -Be 1
        ($output -join "`n") | Should -Match "REJECTED"
    }

    It "rejects mismatched case sets" {
        $results = Join-Path $TestDrive "mismatch"
        & $Runner -Baseline -ResultsDir $results
        & $Runner -Candidate "rules-r1-r3" -Case B01 -ResultsDir $results
        $baselineTemplate = (Get-ChildItem $results -Filter "baseline-*.json").FullName
        $candidateTemplate = (Get-ChildItem $results -Filter "candidate-*.json").FullName
        $baseline = Join-Path $results "scored-baseline.json"
        $candidate = Join-Path $results "scored-candidate.json"
        New-CompletedAssessment -TemplatePath $baselineTemplate -OutputPath $baseline
        New-CompletedAssessment -TemplatePath $candidateTemplate -OutputPath $candidate

        $output = & $Comparer -Run1 "scored-baseline" -Run2 "scored-candidate" -ResultsDir $results
        $LASTEXITCODE | Should -Be 2
        ($output -join "`n") | Should -Match "case sets differ"
    }

    It "rejects a stale scoring digest" {
        $results = Join-Path $TestDrive "stale-scoring"
        & $Runner -Baseline -ResultsDir $results
        & $Runner -Candidate "rules-r1-r3" -ResultsDir $results
        $baselineTemplate = (Get-ChildItem $results -Filter "baseline-*.json").FullName
        $candidateTemplate = (Get-ChildItem $results -Filter "candidate-*.json").FullName
        $baseline = Join-Path $results "scored-baseline.json"
        $candidate = Join-Path $results "scored-candidate.json"
        New-CompletedAssessment -TemplatePath $baselineTemplate -OutputPath $baseline
        New-CompletedAssessment -TemplatePath $candidateTemplate -OutputPath $candidate
        $candidateRecord = Get-Content -Raw $candidate | ConvertFrom-Json -Depth 20
        $candidateRecord.scoringDigest = "0" * 64
        $candidateRecord | ConvertTo-Json -Depth 20 | Set-Content -Encoding utf8 $candidate

        $output = & $Comparer -Run1 "scored-baseline" -Run2 "scored-candidate" -ResultsDir $results
        $LASTEXITCODE | Should -Be 2
        ($output -join "`n") | Should -Match "scoring contract is stale"
    }

    It "rejects a response digest mismatch" {
        $results = Join-Path $TestDrive "response-digest"
        & $Runner -Baseline -ResultsDir $results
        & $Runner -Candidate "rules-r1-r3" -ResultsDir $results
        $baselineTemplate = (Get-ChildItem $results -Filter "baseline-*.json").FullName
        $candidateTemplate = (Get-ChildItem $results -Filter "candidate-*.json").FullName
        $baseline = Join-Path $results "scored-baseline.json"
        $candidate = Join-Path $results "scored-candidate.json"
        New-CompletedAssessment -TemplatePath $baselineTemplate -OutputPath $baseline
        New-CompletedAssessment -TemplatePath $candidateTemplate -OutputPath $candidate
        "tampered" | Set-Content -Encoding utf8 (Join-Path $results "responses\B01.md")

        $output = & $Comparer -Run1 "scored-baseline" -Run2 "scored-candidate" -ResultsDir $results
        $LASTEXITCODE | Should -Be 2
        ($output -join "`n") | Should -Match "Response digest mismatch"
    }

    It "keeps rule and skill activation contracts explicit" {
        $rulesRoot = Join-Path $RepoRoot ".cursor\rules"
        (Get-Content -Raw (Join-Path $rulesRoot "repository-truthfulness.mdc")) |
            Should -Match "alwaysApply:\s*true"
        foreach ($name in @("documentation-ownership.mdc", "validation-integrity.mdc")) {
            (Get-Content -Raw (Join-Path $rulesRoot $name)) | Should -Match "alwaysApply:\s*false"
        }

        foreach ($name in @("review-kagent-capability", "sync-educational-slice")) {
            $skill = Get-Content -Raw (Join-Path $RepoRoot ".agents\skills\$name\SKILL.md")
            $skill | Should -Match "(?m)^name:\s*$name$"
            $skill | Should -Match "(?m)^disable-model-invocation:\s*true$"
        }
    }
}
