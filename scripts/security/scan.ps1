<#
.SYNOPSIS
    Security scan with Trivy.

.PARAMETER Required
    Fail when Trivy is unavailable or returns a nonzero exit code.
    Default (no switch) retains exit-0 and skip behavior for local development use.
#>
param(
    [switch]$Required
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ignoreFile = Join-Path $repoRoot '.trivyignore.yaml'

if (-not (Get-Command trivy -ErrorAction SilentlyContinue)) {
    if ($Required) {
        Write-Error "[FAIL] trivy is not installed (Required mode)"
        exit 1
    }
    Write-Output "[SKIP] trivy not installed"
    exit 0
}

if (-not (Test-Path -LiteralPath $ignoreFile -PathType Leaf)) {
    Write-Error "[FAIL] Trivy scoped ignore configuration is missing: $ignoreFile"
    exit 1
}

Write-Output "=== Trivy filesystem scan ==="
$exitCode = 1
if ($Required) {
    trivy fs --scanners vuln,secret,misconfig --include-dev-deps --ignorefile $ignoreFile --exit-code 1 .
    $exitCode = $LASTEXITCODE
} else {
    trivy fs --scanners vuln,secret,misconfig --ignorefile $ignoreFile --exit-code 0 .
    $exitCode = $LASTEXITCODE
}

if ($exitCode -ne 0) {
    Write-Error "[FAIL] Trivy detected policy-breaking findings (exit code $exitCode)"
    exit $exitCode
}

Write-Output "=== Security scan complete ==="
