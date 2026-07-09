<#
.SYNOPSIS
    Check kagent cluster, agent, and A2A health.
.DESCRIPTION
    Inspects the kagent namespace and reports on:
    - pod readiness
    - agent Accepted/Ready conditions
    - RemoteMCPServer status
    - recent events
    - key pod logs on failure
.PARAMETER Namespace
    Kubernetes namespace for kagent (default: kagent).
.PARAMETER ControllerPort
    Local port for controller port-forward (default: 8083).
.PARAMETER UIPort
    Local port for UI port-forward (default: 8080).
.EXAMPLE
    .\scripts\kagent\check-kagent-health.ps1
    .\scripts\kagent\check-kagent-health.ps1 -Namespace kagent
#>

param(
    [string]$Namespace = "kagent",
    [int]$ControllerPort = 8083,
    [int]$UIPort = 8080
)

$ErrorActionPreference = "Continue"
$exitCode = 0
$failures = @()
$divider = '=' * 60
$notReady = @()

Write-Output $divider
Write-Output "kagent Health Check"
Write-Output "Namespace: $Namespace"
Write-Output "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Output $divider

# --- Section 1: Pod health ---
Write-Output ""
Write-Output "--- Pod Health ---"
$pods = kubectl get pods -n $Namespace --no-headers 2>$null
if (-not $pods) {
    Write-Output "[FAIL] No pods found in namespace $Namespace"
    $failures += "No pods in $Namespace"
    $exitCode = 1
} else {
    $notReady = @()
    $pods | ForEach-Object {
        $parts = $_ -split '\s+'
        $name = $parts[0]
        $ready = $parts[1]
        $status = $parts[2]
        $restarts = $parts[3]
        if ($status -ne "Running" -or $ready -notlike "*1/1*") {
            $notReady += "$name ($status, $ready, restarts=$restarts)"
            Write-Output "[FAIL] $name  $ready  $status  restarts=$restarts"
        } else {
            Write-Output "[PASS] $name  $ready  $status  restarts=$restarts"
        }
    }
    if ($notReady.Count -gt 0) {
        $failures += "Unhealthy pods: $($notReady.Count)"
        $exitCode = 1
    }
}

# --- Section 2: Agent health ---
Write-Output ""
Write-Output "--- Agent Health ---"
$agents = kubectl get agent -n $Namespace --no-headers 2>$null
if (-not $agents) {
    Write-Output "[FAIL] No agents found in namespace $Namespace"
    $failures += "No agents in $Namespace"
    $exitCode = 1
} else {
    $agents | ForEach-Object {
        $parts = $_ -split '\s+'
        $name = $parts[0]
        $type = $parts[1]
        $runtime = $parts[2]
        $ready = $parts[3]
        $accepted = $parts[4]

        $acceptedOk = $accepted -eq "True"
        $readyOk = $ready -eq "True"

        if ($acceptedOk -and $readyOk) {
            Write-Output "[PASS] $name  accepted=$accepted  ready=$ready"
        } elseif ($acceptedOk) {
            Write-Output "[WARN] $name  accepted=$accepted  ready=$ready (not ready yet)"
        } else {
            Write-Output "[FAIL] $name  accepted=$accepted  ready=$ready"
            $failures += "Agent $name not accepted"
            $exitCode = 1
        }
    }
}

# --- Section 3: RemoteMCPServer health ---
Write-Output ""
Write-Output "--- RemoteMCPServer Health ---"
$servers = kubectl get remotemcpserver -n $Namespace --no-headers 2>$null
if (-not $servers) {
    Write-Output "  No RemoteMCPServer resources found (ok for a fresh install)"
} else {
    $servers | ForEach-Object {
        $parts = $_ -split '\s+'
        $name = $parts[0]
        $protocol = $parts[1]
        $url = $parts[2]
        $accepted = $parts[3]

        $acceptedOk = $accepted -eq "True"
        if ($acceptedOk) {
            Write-Output "[PASS] $name  $url  accepted=$accepted"
        } else {
            Write-Output "[INFO] $name  $url  accepted=$accepted (expected if actual MCP server is not deployed)"
        }
    }
}

# --- Section 4: Recent events ---
Write-Output ""
Write-Output "--- Recent Events (last 5) ---"
$events = kubectl get events -n $Namespace --sort-by=.lastTimestamp --no-headers 2>$null
if ($events) {
    $events | Select-Object -Last 5 | ForEach-Object {
        Write-Output "  $_"
    }
} else {
    Write-Output "  No events"
}

# --- Section 5: Check port-forward targets ---
Write-Output ""
Write-Output "--- Service Endpoints ---"
$svc = kubectl get svc -n $Namespace --no-headers 2>$null
if ($svc) {
    $svc | ForEach-Object {
        $parts = $_ -split '\s+'
        $name = $parts[0]
        $clusterIp = $parts[2]
        $ports = $parts[4]
        if ($name -eq "kagent-ui") {
            Write-Output "[INFO] $name  $clusterIp  $ports  (port-forward: kubectl port-forward -n $Namespace svc/$name $($UIPort):8080)"
        } elseif ($name -eq "kagent-controller") {
            Write-Output "[INFO] $name  $clusterIp  $ports  (port-forward: kubectl port-forward -n $Namespace svc/$name $($ControllerPort):8083)"
        } else {
            Write-Output "[INFO] $name  $clusterIp  $ports"
        }
    }
}

# --- Summary ---
Write-Output ""

# Compute aggregate summary
$podCount = ($pods | Measure-Object).Count
$podReady = $podCount - $notReady.Count
$agentCount = ($agents | Measure-Object).Count
$agentReady = 0
$agents | ForEach-Object {
    $parts = $_ -split '\s+'
    if ($parts[3] -eq "True" -and $parts[4] -eq "True") { $agentReady++ }
}
$serverCount = ($servers | Measure-Object).Count
$serverAccepted = 0
$servers | ForEach-Object {
    $parts = $_ -split '\s+'
    if ($parts[3] -eq "True") { $serverAccepted++ }
}
Write-Output "Summary: $podReady/$podCount pods ready, $agentReady/$agentCount agents accepted+ready, $serverCount RemoteMCPServer(s) present ($serverAccepted accepted)"

Write-Output $divider
if ($failures.Count -eq 0) {
    Write-Output "RESULT: ALL CHECKS PASSED"
    Write-Output "kagent namespace is healthy."
} else {
    Write-Output "RESULT: $($failures.Count) failure(s)"
    $failures | ForEach-Object { Write-Output "  - $_" }
    Write-Output ""
    Write-Output "Troubleshooting tips:"
    Write-Output "  kubectl describe pod -n $Namespace <pod-name>"
    Write-Output "  kubectl logs -n $Namespace <pod-name>"
    Write-Output "  kubectl describe agent -n $Namespace <agent-name>"
    Write-Output "  kubectl get events -n $Namespace --sort-by=.lastTimestamp"
}
Write-Output $divider
exit $exitCode
