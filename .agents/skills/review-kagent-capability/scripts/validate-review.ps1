[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Stop-InvalidReview {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Error "INVALID_CAPABILITY_REVIEW: $Message" -ErrorAction Continue
    exit 2
}

try {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Stop-InvalidReview "File does not exist: $Path"
    }

    $document = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json -Depth 20
    if ($document.schemaVersion -ne "1.0") {
        Stop-InvalidReview "schemaVersion must equal 1.0."
    }
    if ($null -eq $document.review) {
        Stop-InvalidReview "review is required."
    }

    $review = $document.review
    if ([string]::IsNullOrWhiteSpace([string]$review.scope)) {
        Stop-InvalidReview "review.scope is required."
    }
    $observedAt = [DateTimeOffset]::MinValue
    if (
        -not [DateTimeOffset]::TryParse(
            [string]$review.observedAt,
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::RoundtripKind,
            [ref]$observedAt
        )
    ) {
        Stop-InvalidReview "review.observedAt must be an ISO-8601 timestamp."
    }

    $claims = @($review.claims)
    if ($claims.Count -eq 0) {
        Stop-InvalidReview "At least one claim is required."
    }

    $allowedClassifications = @("Proven", "Not proven", "Blocked", "Not attempted")
    foreach ($claim in $claims) {
        if ([string]$claim.level -notmatch "^L[0-7]$") {
            Stop-InvalidReview "Every claim.level must be L0 through L7."
        }
        if ([string]$claim.classification -notin $allowedClassifications) {
            Stop-InvalidReview "Unknown classification for $($claim.level)."
        }
        if ([string]::IsNullOrWhiteSpace([string]$claim.claim)) {
            Stop-InvalidReview "Every claim requires the text being assessed."
        }
        if ([string]::IsNullOrWhiteSpace([string]$claim.rationale)) {
            Stop-InvalidReview "Every claim requires a rationale."
        }
        $sources = @($claim.sources)
        if ($sources.Count -eq 0 -or @($sources | Where-Object {
            [string]::IsNullOrWhiteSpace([string]$_)
        }).Count -gt 0) {
            Stop-InvalidReview "Every claim requires at least one non-empty source."
        }
        if (
            $claim.classification -eq "Proven" -and
            $claim.promotionCriteriaChecked -ne $true
        ) {
            Stop-InvalidReview "A Proven claim requires promotionCriteriaChecked=true."
        }
    }

    if ($null -eq $review.verdict) {
        Stop-InvalidReview "review.verdict is required."
    }
    $expected = [ordered]@{
        claimsChecked = $claims.Count
        proven = @($claims | Where-Object classification -EQ "Proven").Count
        notProven = @($claims | Where-Object classification -EQ "Not proven").Count
        blocked = @($claims | Where-Object classification -EQ "Blocked").Count
        notAttempted = @($claims | Where-Object classification -EQ "Not attempted").Count
    }
    foreach ($name in $expected.Keys) {
        if ([int]$review.verdict.$name -ne [int]$expected[$name]) {
            Stop-InvalidReview "review.verdict.$name does not match the claim classifications."
        }
    }
    if ($review.verdict.currentStatusChanged -isnot [bool]) {
        Stop-InvalidReview "review.verdict.currentStatusChanged must be boolean."
    }
    if ([string]::IsNullOrWhiteSpace([string]$review.verdict.summary)) {
        Stop-InvalidReview "review.verdict.summary is required."
    }

    [pscustomobject]@{
        schemaVersion = "1.0"
        valid = $true
        claimsChecked = $claims.Count
        classifications = [pscustomobject]$expected
    } | ConvertTo-Json -Depth 5
    exit 0
} catch {
    Stop-InvalidReview $_.Exception.Message
}
