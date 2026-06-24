<#
.SYNOPSIS
    Validate Kubernetes manifests with kubeconform and kube-linter.
#>
$ErrorActionPreference = "Stop"
if (-not (Get-Command kubeconform -ErrorAction SilentlyContinue)) {
    Write-Output "[SKIP] kubeconform not installed"
} else {
    Write-Output "=== kubeconform ==="; kubeconform -strict -summary deploy/
}
if (-not (Get-Command kube-linter -ErrorAction SilentlyContinue)) {
    Write-Output "[SKIP] kube-linter not installed"
} else {
    Write-Output "=== kube-linter ==="; kube-linter lint deploy/
}
Write-Output "=== Kubernetes validation complete ==="
