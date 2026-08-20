# Apply LiteLLM ModelConfig + Secret for kagent (PR2). No secrets printed.
# Manual-first. Requires: kubectl context docker-desktop, ns kagent, LiteLLM on :4000.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root

$ctx = kubectl config current-context
if ($ctx -ne "docker-desktop") {
    Write-Error "Expected kubectl context docker-desktop, got: $ctx"
}

$master = [Environment]::GetEnvironmentVariable("LITELLM_MASTER_KEY", "User")
if (-not $master) {
    Write-Error "LITELLM_MASTER_KEY missing in User scope"
}

Write-Output "=== Ensure Secret kagent-litellm (key only; no provider keys) ==="
$ErrorActionPreference = "Continue"
kubectl get secret kagent-litellm -n kagent -o name 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    kubectl delete secret kagent-litellm -n kagent | Out-Null
}
$ErrorActionPreference = "Stop"
kubectl create secret generic kagent-litellm `
    -n kagent `
    --from-literal=LITELLM_MASTER_KEY=$master | Out-Null
Write-Output "Secret applied (value not shown)."

Write-Output "=== Apply ModelConfig and one no-tool smoke agent ==="
kubectl apply -f deploy/samples/kagent/litellm-gateway-model-config.yaml
if ($LASTEXITCODE -ne 0) { Write-Error "kubectl apply failed" }
kubectl apply -f deploy/samples/kagent/litellm-gateway-smoke-agent.yaml
if ($LASTEXITCODE -ne 0) { Write-Error "smoke agent apply failed" }

Write-Output "=== ModelConfig status ==="
kubectl get modelconfig litellm-gateway-model-config -n kagent -o yaml |
    Select-String -Pattern "name:|model:|baseUrl:|apiKeySecret:|provider:"

Write-Output "=== Smoke agent status ==="
kubectl get agent litellm-gateway-smoke-agent -n kagent -o yaml |
    Select-String -Pattern "name:|modelConfig:|Accepted|Ready"

Write-Output "Done. Next: port-forward controller if needed, then test-a2a-agent.py task."
