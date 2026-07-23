<#
.SYNOPSIS
    Validate and compare two agent-governance benchmark assessments.
.DESCRIPTION
    Recomputes completion and hard-gate results from case-level values. It
    rejects missing, malformed, stale, or mismatched records and never trusts
    the stored summary.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[a-zA-Z0-9][a-zA-Z0-9._-]*$")]
    [string]$Run1,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[a-zA-Z0-9][a-zA-Z0-9._-]*$")]
    [string]$Run2,

    [string]$ResultsDir = (Join-Path $PSScriptRoot "results")
)

$ErrorActionPreference = "Stop"

function Resolve-RunPath {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Directory
    )

    $fileName = if ($Name.EndsWith(".json", [StringComparison]::OrdinalIgnoreCase)) {
        $Name
    } else {
        "$Name.json"
    }
    $root = [IO.Path]::GetFullPath($Directory)
    $path = [IO.Path]::GetFullPath((Join-Path $root $fileName))
    $prefix = $root.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) +
        [IO.Path]::DirectorySeparatorChar
    if (-not $path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Run path escapes results directory: $Name"
    }
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Run not found: $path"
    }
    return $path
}

function Read-Assessment {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$Scoring,
        [Parameter(Mandatory = $true)][string]$ScoringDigest
    )

    try {
        $record = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json -Depth 20
    } catch {
        throw "Invalid assessment JSON '$Path': $($_.Exception.Message)"
    }

    if ($record.schemaVersion -ne "1.0") {
        throw "Unsupported assessment schemaVersion in '$Path'."
    }
    if ($record.mode -notin @("baseline", "candidate")) {
        throw "Invalid assessment mode in '$Path'."
    }
    if ($record.scoringDigest -ne $ScoringDigest) {
        throw "Assessment scoring contract is stale or mismatched: '$Path'."
    }
    if (@($record.cases).Count -eq 0) {
        throw "Assessment has no cases: '$Path'."
    }

    $knownGates = @($Scoring.hardGates.PSObject.Properties.Name)
    $knownMeasures = @($Scoring.softMeasures.PSObject.Properties.Name)
    $seenIds = @{}
    $incompleteFields = [Collections.Generic.List[string]]::new()
    $failedHardGates = 0
    $evaluatedHardGates = 0
    $softTotals = @{}
    $softCounts = @{}

    foreach ($field in @("executor", "model", "workspaceRevision", "customizationState")) {
        $value = $record.executionContext.PSObject.Properties[$field].Value
        if ([string]::IsNullOrWhiteSpace([string]$value)) {
            $incompleteFields.Add("executionContext.$field")
        }
    }
    if ($record.mode -eq "baseline" -and $record.executionContext.customizationState -ne "none") {
        throw "Baseline customizationState must be 'none' in '$Path'."
    }
    if ($record.mode -eq "candidate" -and $record.executionContext.customizationState -eq "none") {
        throw "Candidate customizationState cannot be 'none' in '$Path'."
    }

    foreach ($name in $knownMeasures) {
        $softTotals[$name] = 0.0
        $softCounts[$name] = 0
    }

    foreach ($case in @($record.cases)) {
        if ($case.id -notmatch "^B(?:0[1-9]|10)$") {
            throw "Invalid case id '$($case.id)' in '$Path'."
        }
        if ($seenIds.ContainsKey($case.id)) {
            throw "Duplicate case id '$($case.id)' in '$Path'."
        }
        $seenIds[$case.id] = $true

        $contractProperty = $Scoring.cases.PSObject.Properties[$case.id]
        if ($null -eq $contractProperty) {
            throw "Unknown case id '$($case.id)' in '$Path'."
        }
        $contract = $contractProperty.Value
        $casePath = Join-Path $PSScriptRoot $contract.source
        if (-not (Test-Path -LiteralPath $casePath -PathType Leaf)) {
            throw "Current case source is missing for $($case.id)."
        }
        $currentCaseDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $casePath).Hash.ToLowerInvariant()
        if ($case.caseDigest -ne $currentCaseDigest) {
            throw "Assessment case source is stale or mismatched for $($case.id)."
        }

        $actualGateNames = @($case.hardGates.PSObject.Properties.Name | Sort-Object)
        $requiredGateNames = @($contract.requiredHardGates | Sort-Object)
        if (($actualGateNames -join "|") -ne ($requiredGateNames -join "|")) {
            throw "Hard-gate set mismatch for $($case.id) in '$Path'."
        }

        foreach ($gateName in $requiredGateNames) {
            if ($gateName -notin $knownGates) {
                throw "Unknown hard gate '$gateName' in '$Path'."
            }
            $value = $case.hardGates.$gateName
            if ($null -eq $value) {
                $incompleteFields.Add("$($case.id).hardGates.$gateName")
                continue
            }
            if ($value -isnot [int] -and $value -isnot [long]) {
                throw "Hard gate '$gateName' for $($case.id) must be an integer."
            }
            if ([int64]$value -lt 0) {
                throw "Hard gate '$gateName' for $($case.id) cannot be negative."
            }
            $evaluatedHardGates++
            if ([int64]$value -ne [int64]$Scoring.hardGates.$gateName.requiredValue) {
                $failedHardGates++
            }
        }

        foreach ($measureName in $knownMeasures) {
            $property = $case.softMeasures.PSObject.Properties[$measureName]
            if ($null -eq $property -or $null -eq $property.Value) {
                $incompleteFields.Add("$($case.id).softMeasures.$measureName")
                continue
            }
            if ($property.Value -isnot [ValueType]) {
                throw "Soft measure '$measureName' for $($case.id) must be numeric."
            }
            $number = [double]$property.Value
            if ($number -lt 0) {
                throw "Soft measure '$measureName' for $($case.id) cannot be negative."
            }
            if ($measureName -eq "validationCoverage" -and $number -gt 1) {
                throw "validationCoverage for $($case.id) must be between 0 and 1."
            }
            $softTotals[$measureName] += $number
            $softCounts[$measureName]++
        }

        if ([string]::IsNullOrWhiteSpace([string]$case.responseArtifact)) {
            $incompleteFields.Add("$($case.id).responseArtifact")
        } else {
            $assessmentRoot = [IO.Path]::GetFullPath((Split-Path -Parent $Path))
            $responsePath = [IO.Path]::GetFullPath((Join-Path $assessmentRoot $case.responseArtifact))
            $prefix = $assessmentRoot.TrimEnd(
                [IO.Path]::DirectorySeparatorChar,
                [IO.Path]::AltDirectorySeparatorChar
            ) + [IO.Path]::DirectorySeparatorChar
            if (-not $responsePath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Response artifact escapes the assessment directory for $($case.id)."
            }
            if (-not (Test-Path -LiteralPath $responsePath -PathType Leaf)) {
                $incompleteFields.Add("$($case.id).responseArtifact")
            } elseif ([string]::IsNullOrWhiteSpace([string]$case.responseDigest)) {
                $incompleteFields.Add("$($case.id).responseDigest")
            } else {
                $actualResponseDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $responsePath).Hash.ToLowerInvariant()
                if ($case.responseDigest -ne $actualResponseDigest) {
                    throw "Response digest mismatch for $($case.id)."
                }
            }
        }
        if ([string]::IsNullOrWhiteSpace([string]$case.assessor)) {
            $incompleteFields.Add("$($case.id).assessor")
        }
    }

    $softAverages = @{}
    foreach ($measureName in $knownMeasures) {
        $softAverages[$measureName] = if ($softCounts[$measureName] -gt 0) {
            $softTotals[$measureName] / $softCounts[$measureName]
        } else {
            $null
        }
    }

    [pscustomobject]@{
        Label = [string]$record.label
        Mode = [string]$record.mode
        CaseIds = @($seenIds.Keys | Sort-Object)
        Complete = $incompleteFields.Count -eq 0
        IncompleteFields = @($incompleteFields)
        FailedHardGates = $failedHardGates
        EvaluatedHardGates = $evaluatedHardGates
        SoftAverages = $softAverages
    }
}

try {
    $scoringPath = Join-Path $PSScriptRoot "scoring.json"
    $scoring = Get-Content -Raw -LiteralPath $scoringPath | ConvertFrom-Json -Depth 20
    if ($scoring.schemaVersion -ne "1.0") {
        throw "Unsupported scoring schemaVersion."
    }
    $scoringDigest = (Get-FileHash -Algorithm SHA256 -LiteralPath $scoringPath).Hash.ToLowerInvariant()

    $assessment1 = Read-Assessment `
        -Path (Resolve-RunPath -Name $Run1 -Directory $ResultsDir) `
        -Scoring $scoring `
        -ScoringDigest $scoringDigest
    $assessment2 = Read-Assessment `
        -Path (Resolve-RunPath -Name $Run2 -Directory $ResultsDir) `
        -Scoring $scoring `
        -ScoringDigest $scoringDigest
} catch {
    Write-Output "INVALID: $($_.Exception.Message)"
    exit 2
}

if (($assessment1.CaseIds -join "|") -ne ($assessment2.CaseIds -join "|")) {
    Write-Output "INVALID: assessment case sets differ."
    exit 2
}
if ($assessment1.Mode -ne "baseline" -or $assessment2.Mode -ne "candidate") {
    Write-Output "INVALID: Run1 must be a baseline and Run2 must be a candidate."
    exit 2
}
if (-not $assessment1.Complete -or -not $assessment2.Complete) {
    Write-Output "INCOMPLETE: benchmark comparison is not eligible for a decision."
    if (-not $assessment1.Complete) {
        Write-Output "$($assessment1.Label): $($assessment1.IncompleteFields.Count) missing fields."
    }
    if (-not $assessment2.Complete) {
        Write-Output "$($assessment2.Label): $($assessment2.IncompleteFields.Count) missing fields."
    }
    exit 2
}

Write-Output "Baseline: $($assessment1.Label)"
Write-Output "Candidate: $($assessment2.Label)"
Write-Output "Baseline hard-gate failures: $($assessment1.FailedHardGates)"
Write-Output "Candidate hard-gate failures: $($assessment2.FailedHardGates)"
Write-Output "Soft measure averages (baseline -> candidate):"
foreach ($measureName in @($scoring.softMeasures.PSObject.Properties.Name | Sort-Object)) {
    $baselineValue = $assessment1.SoftAverages[$measureName]
    $candidateValue = $assessment2.SoftAverages[$measureName]
    $direction = $scoring.softMeasures.$measureName.direction
    Write-Output "  $measureName ($direction): $baselineValue -> $candidateValue"
}

$hardGateRegression = $assessment2.FailedHardGates -gt $assessment1.FailedHardGates
$candidatePassed = $assessment2.FailedHardGates -eq 0
if ($hardGateRegression -or -not $candidatePassed) {
    Write-Output "DECISION: REJECTED"
    exit 1
}

Write-Output "DECISION: HARD_GATES_PASSED"
Write-Output "Soft measures require human review before promotion."
exit 0
