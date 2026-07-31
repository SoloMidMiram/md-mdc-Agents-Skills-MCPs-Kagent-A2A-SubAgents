<#
.SYNOPSIS
    Initialize or compare agent-governance benchmark assessments.
.DESCRIPTION
    Creates an unscored JSON assessment template from the frozen case and
    scoring contracts. It does not execute an agent and never reports an
    unscored template as a benchmark pass.
.PARAMETER Baseline
    Initialize a baseline assessment.
.PARAMETER Candidate
    Initialize a candidate assessment with a lowercase kebab-case label.
.PARAMETER Compare
    Compare two complete assessment labels or JSON filenames.
.PARAMETER Case
    Initialize one case (for example, B01). Omit to include all cases.
.PARAMETER ResultsDir
    Generated-output directory. It must not be committed.
#>

[CmdletBinding(DefaultParameterSetName = "Help")]
param(
    [Parameter(Mandatory = $true, ParameterSetName = "Baseline")]
    [switch]$Baseline,

    [Parameter(Mandatory = $true, ParameterSetName = "Candidate")]
    [ValidatePattern("^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    [string]$Candidate,

    [Parameter(Mandatory = $true, ParameterSetName = "Compare")]
    [ValidateCount(2, 2)]
    [string[]]$Compare,

    [Parameter(ParameterSetName = "Baseline")]
    [Parameter(ParameterSetName = "Candidate")]
    [ValidatePattern("^B(?:0[1-9]|10)$")]
    [string]$Case,

    [string]$ResultsDir = (Join-Path $PSScriptRoot "results")
)

$ErrorActionPreference = "Stop"

if ($PSCmdlet.ParameterSetName -eq "Compare") {
    & (Join-Path $PSScriptRoot "compare-benchmark.ps1") `
        -Run1 $Compare[0] `
        -Run2 $Compare[1] `
        -ResultsDir $ResultsDir
    exit $LASTEXITCODE
}

if ($PSCmdlet.ParameterSetName -eq "Help") {
    Write-Output "INVALID: use -Baseline, -Candidate <label>, or -Compare <run1> <run2>."
    exit 2
}

$scoringPath = Join-Path $PSScriptRoot "scoring.json"
if (-not (Test-Path -LiteralPath $scoringPath -PathType Leaf)) {
    Write-Output "INVALID: scoring contract not found: $scoringPath"
    exit 2
}

try {
    $scoring = Get-Content -Raw -LiteralPath $scoringPath | ConvertFrom-Json -Depth 20
} catch {
    Write-Output "INVALID: scoring contract is invalid JSON: $($_.Exception.Message)"
    exit 2
}

if ($scoring.schemaVersion -ne "1.0") {
    Write-Output "INVALID: unsupported scoring schemaVersion: $($scoring.schemaVersion)"
    exit 2
}

$selectedIds = @($scoring.cases.PSObject.Properties.Name | Sort-Object)
if ($Case) {
    $selectedIds = @($selectedIds | Where-Object { $_ -eq $Case })
}
if ($selectedIds.Count -eq 0) {
    Write-Output "INVALID: no scoring case matched '$Case'."
    exit 2
}

$cases = foreach ($caseId in $selectedIds) {
    $caseContract = $scoring.cases.$caseId
    $casePath = Join-Path $PSScriptRoot $caseContract.source
    if (-not (Test-Path -LiteralPath $casePath -PathType Leaf)) {
        Write-Output "INVALID: case source for $caseId not found: $casePath"
        exit 2
    }

    $caseText = Get-Content -Raw -LiteralPath $casePath
    $firstLine = ($caseText -split "\r?\n", 2)[0].Trim()
    if ($firstLine -match "^#\s+${caseId}:\s+(.+)$") {
        $caseTitle = $Matches[1]
    } else {
        Write-Output "INVALID: case source heading must start with '# ${caseId}:': $casePath"
        exit 2
    }

    $hardGates = [ordered]@{}
    foreach ($gateName in $caseContract.requiredHardGates) {
        if (-not $scoring.hardGates.PSObject.Properties[$gateName]) {
            Write-Output "INVALID: case $caseId references unknown hard gate '$gateName'."
            exit 2
        }
        $hardGates[$gateName] = $null
    }

    $softMeasures = [ordered]@{}
    foreach ($measureName in $scoring.softMeasures.PSObject.Properties.Name) {
        $softMeasures[$measureName] = $null
    }

    [ordered]@{
        id = $caseId
        title = $caseTitle
        source = $caseContract.source
        caseDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $casePath).Hash.ToLowerInvariant()
        responseArtifact = $null
        responseDigest = $null
        assessor = $null
        hardGates = $hardGates
        softMeasures = $softMeasures
        notes = ""
    }
}

$now = (Get-Date).ToUniversalTime()
$timestamp = $now.ToString("yyyy-MM-ddTHHmmssZ")
$mode = if ($Baseline) { "baseline" } else { "candidate" }
$label = if ($Baseline) {
    "baseline-$timestamp"
} else {
    "candidate-$Candidate-$timestamp"
}

$record = [ordered]@{
    schemaVersion = "1.0"
    label = $label
    createdAt = $now.ToString("o")
    mode = $mode
    candidateLabel = if ($Candidate) { $Candidate } else { $null }
    scoringDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $scoringPath).Hash.ToLowerInvariant()
    executionContext = [ordered]@{
        executor = $null
        model = $null
        workspaceRevision = $null
        customizationState = if ($Baseline) { "none" } else { $Candidate }
    }
    status = "unscored"
    cases = @($cases)
    summary = [ordered]@{
        complete = $false
        totalCases = @($cases).Count
        scoredCases = 0
        totalHardGates = (@($cases) | ForEach-Object { $_.hardGates.Count } | Measure-Object -Sum).Sum
        evaluatedHardGates = 0
        failedHardGates = $null
        decision = "not_evaluated"
    }
}

New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null
$outputPath = Join-Path $ResultsDir "$label.json"
$record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $outputPath -Encoding utf8

Write-Output "Benchmark assessment template created."
Write-Output "This command did not run an agent and did not score a result."
Write-Output "Cases: $(@($cases).Count)"
Write-Output "Output: $outputPath"
Write-Output "Next: run each case in a fresh context, save the response artifact, score every required field, then compare complete JSON records."
exit 0
