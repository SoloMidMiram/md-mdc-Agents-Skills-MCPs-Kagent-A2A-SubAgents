<#
.SYNOPSIS
    Security scan with Trivy.
#>
$ErrorActionPreference = "Stop"
if (-not (Get-Command trivy -ErrorAction SilentlyContinue)) {
    Write-Output "[SKIP] trivy not installed"
    exit 0
}
Write-Output "=== Trivy filesystem scan ==="
trivy fs --scanners vuln,secret,misconfig --exit-code 0 .
Write-Output "=== Security scan complete ==="
