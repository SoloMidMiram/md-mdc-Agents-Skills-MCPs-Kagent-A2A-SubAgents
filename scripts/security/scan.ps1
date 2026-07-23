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

if (-not (Get-Command trivy -ErrorAction SilentlyContinue)) {
    if ($Required) {
        Write-Error "[FAIL] trivy is not installed (Required mode)"
        exit 1
    }
    Write-Output "[SKIP] trivy not installed"
    exit 0
}

Write-Output "=== Trivy filesystem scan ==="
$exitCode = 1
if ($Required) {
    trivy fs --scanners vuln,secret,misconfig --exit-code 1 .
    $exitCode = $LASTEXITCODE
} else {
    trivy fs --scanners vuln,secret,misconfig --exit-code 0 .
    $exitCode = $LASTEXITCODE
}

if ($exitCode -ne 0) {
    Write-Error "[FAIL] Trivy detected policy-breaking findings (exit code $exitCode)"
    exit $exitCode
}

Write-Output "=== Security scan complete ==="
