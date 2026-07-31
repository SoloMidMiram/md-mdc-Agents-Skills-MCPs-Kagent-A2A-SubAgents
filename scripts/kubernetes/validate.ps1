<#
.SYNOPSIS
    Validate Kubernetes manifests with kubeconform and kube-linter.

.PARAMETER Strict
    Fail when a required tool is missing or returns a nonzero exit code.
    Default (no switch) retains fail-open behavior for local development use.
#>
param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$exitCode = 0

# --- kubeconform ---
if (-not (Get-Command kubeconform -ErrorAction SilentlyContinue)) {
    if ($Strict) {
        Write-Error "[FAIL] kubeconform is not installed (Strict mode)"
        $exitCode = 1
    } else {
        Write-Output "[SKIP] kubeconform not installed"
    }
} else {
    Write-Output "=== kubeconform ==="
    # --ignore-missing-schemas avoids failures on CRDs (RemoteMCPServer, Agent, etc.)
    # that kubeconform cannot validate without their CRD schemas.
    kubeconform -strict -ignore-missing-schemas -summary deploy/
    $lastExit = $LASTEXITCODE
    if ($lastExit -ne 0) {
        Write-Error "[FAIL] kubeconform exited with code $lastExit"
        $exitCode = 1
    }
}

# --- kube-linter ---
if (-not (Get-Command kube-linter -ErrorAction SilentlyContinue)) {
    if ($Strict) {
        Write-Error "[FAIL] kube-linter is not installed (Strict mode)"
        $exitCode = 1
    } else {
        Write-Output "[SKIP] kube-linter not installed"
    }
} else {
    Write-Output "=== kube-linter ==="
    kube-linter lint deploy/
    $lastExit = $LASTEXITCODE
    if ($lastExit -ne 0) {
        Write-Error "[FAIL] kube-linter exited with code $lastExit"
        $exitCode = 1
    }
}

if ($exitCode -eq 0) {
    Write-Output "=== Kubernetes validation complete: all checks passed ==="
} else {
    Write-Output "=== Kubernetes validation complete: one or more checks FAILED ==="
    exit $exitCode
}
