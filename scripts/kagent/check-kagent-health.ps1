<#
.SYNOPSIS
    Capability-gated health check for the local kagent educational lab.
.DESCRIPTION
    Collects kubectl observations and evaluates an explicit profile:
    CardLab (default), DirectMcpServer, A2ADispatch, or FullMcpExecution.

    Pure parsing and gate decisions live in KagentHealth.psm1 so they can be
    tested without a cluster. This script owns collection, evidence loading,
    optional A2A attempts, output, and exit codes.
.PARAMETER Profile
    Capability profile to evaluate (default: CardLab).
.PARAMETER Namespace
    Kubernetes namespace (default: kagent).
.PARAMETER OutputFormat
    Human or Json.
.PARAMETER DirectMcpResultPath
    Path to sanitized mcp_session_smoke.py JSON for DirectMcpServer / FullMcpExecution checks.
.PARAMETER AgentToolEvidencePath
    Path to agent-mediated evidence JSON for FullMcpExecution.
.PARAMETER ControllerUrl
    Controller base URL for live A2A dispatch attempts (default http://127.0.0.1:8083).
.PARAMETER SkipLiveA2A
    Do not invoke the A2A helper; require pre-supplied evidence objects via tests only.
.EXAMPLE
    .\scripts\kagent\check-kagent-health.ps1 -Profile CardLab
.EXAMPLE
    .\scripts\kagent\check-kagent-health.ps1 -Profile DirectMcpServer -DirectMcpResultPath .\direct.json -OutputFormat Json
#>

[CmdletBinding()]
param(
    [ValidateSet('CardLab', 'DirectMcpServer', 'A2ADispatch', 'FullMcpExecution')]
    [string]$Profile = 'CardLab',

    [string]$Namespace = 'kagent',

    [ValidateSet('Human', 'Json')]
    [string]$OutputFormat = 'Human',

    [string]$DirectMcpResultPath,

    [string]$AgentToolEvidencePath,

    [string]$ControllerUrl = 'http://127.0.0.1:8083',

    [int]$ControllerPort = 8083,

    [int]$UIPort = 8080,

    [switch]$SkipLiveA2A
)

$ErrorActionPreference = 'Continue'
$modulePath = Join-Path $PSScriptRoot 'KagentHealth.psm1'
Import-Module $modulePath -Force

function Write-Diag {
    param([string]$Message)
    [Console]::Error.WriteLine($Message)
}

function Get-KubectlLines {
    param(
        [Parameter(Mandatory)][string[]]$Arguments
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & kubectl @Arguments 2>$null
        if ($LASTEXITCODE -ne 0) {
            return @{ Ok = $false; Lines = @(); Error = ("kubectl failed (exit {0}): {1}" -f $LASTEXITCODE, ($Arguments -join ' ')) }
        }
        $lines = @()
        if ($null -ne $output) {
            $lines = @($output | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
        }
        return @{ Ok = $true; Lines = $lines; Error = $null }
    }
    catch {
        return @{ Ok = $false; Lines = @(); Error = $_.Exception.Message }
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

function Read-JsonEvidenceFile {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw ("evidence file not found: {0}" -f $Path)
    }
    $raw = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop
    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw ("evidence file is empty: {0}" -f $Path)
    }
    try {
        return ($raw | ConvertFrom-Json -ErrorAction Stop)
    }
    catch {
        throw ("malformed evidence JSON in {0}: {1}" -f $Path, $_.Exception.Message)
    }
}

function Get-A2ADispatchEvidenceFromHelper {
    param(
        [Parameter(Mandatory)][string]$ControllerBase,
        [string]$AgentNamespace = 'kagent',
        [string]$AgentName = 'k8s-a2a-agent'
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
    $helper = Join-Path $repoRoot 'scripts\kagent\test-a2a-agent.py'
    if (-not (Test-Path -LiteralPath $helper)) {
        return [pscustomobject]@{
            schemaVersion  = '1.0'
            transportError = "A2A helper missing: $helper"
        }
    }

    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & python $helper task --controller $ControllerBase --namespace $AgentNamespace --agent $AgentName --output json 2>&1
        $code = $LASTEXITCODE
    }
    catch {
        return [pscustomobject]@{
            schemaVersion  = '1.0'
            transportError = $_.Exception.Message
        }
    }
    finally {
        $ErrorActionPreference = $prev
    }

    $text = ($output | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        return [pscustomobject]@{
            helperExit   = $code
            evidenceError = 'empty helper JSON output'
        }
    }

    try {
        $parsed = $text | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        # Do not scrape human markers; malformed JSON is a local evidence/schema failure.
        return [pscustomobject]@{
            helperExit    = $code
            evidenceError = ('helper JSON parse failed: {0}' -f $_.Exception.Message)
        }
    }

    # Keep the helper contract intact. The evaluator must reject missing schema or
    # inconsistent nested fields rather than accepting collector-derived values.
    $parsed | Add-Member -NotePropertyName helperExit -NotePropertyValue $code -Force
    return $parsed
}

function Get-AgentMediatedEvidenceFromHelper {
    param(
        [Parameter(Mandatory)][string]$ControllerBase,
        [string]$AgentNamespace = 'kagent',
        [string]$AgentName = 'k8s-a2a-agent',
        [string]$ClusterContext = 'docker-desktop'
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
    $helper = Join-Path $repoRoot 'scripts\kagent\agent_mcp_trace.py'
    if (-not (Test-Path -LiteralPath $helper)) {
        throw ("agent MCP trace helper missing: {0}" -f $helper)
    }

    $sourceOut = Join-Path $repoRoot 'evidence\kagent\tmp\agent-mcp-trace-latest.json'
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & python $helper `
            --controller $ControllerBase `
            --namespace $AgentNamespace `
            --agent $AgentName `
            --cluster-context $ClusterContext `
            --output json `
            --source-out $sourceOut 2>&1
        $code = $LASTEXITCODE
    }
    catch {
        throw $_.Exception.Message
    }
    finally {
        $ErrorActionPreference = $prev
    }

    $text = ($output | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        throw 'empty agent_mcp_trace JSON output'
    }
    try {
        $parsed = $text | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw ("agent_mcp_trace JSON parse failed: {0}" -f $_.Exception.Message)
    }
    $parsed | Add-Member -NotePropertyName helperExit -NotePropertyValue $code -Force
    return $parsed
}

# --- Argument / evidence validation (exit 2) before collection where possible ---
try {
    if ($Profile -eq 'DirectMcpServer' -and [string]::IsNullOrWhiteSpace($DirectMcpResultPath)) {
        Write-Diag '[FAIL] DirectMcpServer requires -DirectMcpResultPath'
        exit 2
    }

    $directEvidence = $null
    if (-not [string]::IsNullOrWhiteSpace($DirectMcpResultPath)) {
        $directEvidence = Read-JsonEvidenceFile -Path $DirectMcpResultPath
    }
    $agentEvidence = $null
    if (-not [string]::IsNullOrWhiteSpace($AgentToolEvidencePath)) {
        $agentEvidence = Read-JsonEvidenceFile -Path $AgentToolEvidencePath
    }
}
catch {
    Write-Diag ("[FAIL] {0}" -f $_.Exception.Message)
    exit 2
}

# --- Collection ---
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Diag '[FAIL] kubectl is not available'
    exit 3
}

$podResult = Get-KubectlLines -Arguments @('get', 'pods', '-n', $Namespace, '--no-headers')
if (-not $podResult.Ok) {
    Write-Diag ("[FAIL] {0}" -f $podResult.Error)
    exit 3
}
$agentResult = Get-KubectlLines -Arguments @('get', 'agent', '-n', $Namespace, '--no-headers')
if (-not $agentResult.Ok) {
    Write-Diag ("[FAIL] {0}" -f $agentResult.Error)
    exit 3
}
$serverResult = Get-KubectlLines -Arguments @('get', 'remotemcpserver', '-n', $Namespace, '--no-headers')
# RemoteMCPServer CRD may be absent on a fresh install; treat empty ok, real kubectl errors as transport.
if (-not $serverResult.Ok -and $serverResult.Error -match 'exit [^0]') {
    # Still allow empty list when resource type missing? Prefer fail-closed on kubectl errors.
    Write-Diag ("[FAIL] {0}" -f $serverResult.Error)
    exit 3
}

$pods = @($podResult.Lines | ForEach-Object { ConvertFrom-KubectlPodLine -Line $_ } | Where-Object { $null -ne $_ })
$agents = @($agentResult.Lines | ForEach-Object { ConvertFrom-KubectlAgentLine -Line $_ } | Where-Object { $null -ne $_ })
$servers = @()
if ($serverResult.Ok) {
    $servers = @($serverResult.Lines | ForEach-Object { ConvertFrom-KubectlRemoteMcpServerLine -Line $_ } | Where-Object { $null -ne $_ })
}

$clusterContext = 'docker-desktop'
if ($Profile -eq 'FullMcpExecution') {
    $contextResult = Get-KubectlLines -Arguments @('config', 'current-context')
    if (-not $contextResult.Ok -or $contextResult.Lines.Count -eq 0) {
        Write-Diag '[FAIL] unable to determine kubectl current-context'
        exit 3
    }
    $clusterContext = "$($contextResult.Lines[0])"
}

$a2aEvidence = $null
if ($Profile -eq 'A2ADispatch') {
    if ($SkipLiveA2A) {
        Write-Diag '[FAIL] A2A evidence required but -SkipLiveA2A was set without injectable evidence'
        exit 2
    }
    $a2aEvidence = Get-A2ADispatchEvidenceFromHelper -ControllerBase $ControllerUrl.TrimEnd('/') -AgentNamespace $Namespace
}

if ($Profile -eq 'FullMcpExecution' -and $null -eq $agentEvidence) {
    if ($SkipLiveA2A) {
        Write-Diag '[FAIL] FullMcpExecution requires -AgentToolEvidencePath when -SkipLiveA2A is set'
        exit 2
    }
    try {
        $agentEvidence = Get-AgentMediatedEvidenceFromHelper -ControllerBase $ControllerUrl.TrimEnd('/') -AgentNamespace $Namespace -ClusterContext $clusterContext
    }
    catch {
        Write-Diag ("[FAIL] {0}" -f $_.Exception.Message)
        exit 3
    }
}

$evalParams = @{
    Profile                     = $Profile
    Pods                        = $pods
    Agents                      = $agents
    RemoteMcpServers            = $servers
    DirectMcpEvidence           = $directEvidence
    A2ADispatchEvidence         = $a2aEvidence
    AgentMediatedEvidence       = $agentEvidence
    DirectMcpEvidenceRequired   = ($Profile -eq 'DirectMcpServer')
    A2ADispatchEvidenceRequired = ($Profile -in @('A2ADispatch', 'FullMcpExecution'))
    AgentMediatedEvidenceRequired = ($Profile -eq 'FullMcpExecution')
    ExpectedClusterContext         = $clusterContext
    ExpectedAgentNamespace         = $Namespace
    ExpectedAgentName              = 'k8s-a2a-agent'
    ExpectedControllerOrigin       = $ControllerUrl.TrimEnd('/')
}

$result = Invoke-KagentHealthProfile @evalParams

# Optional informational sections for Human mode (CardLab ergonomics)
if ($OutputFormat -eq 'Human') {
    $human = Format-KagentHealthHuman -Result $result
    Write-Output $human

    # Preserve the original learner-facing event context without making it a gate.
    Write-Output ''
    Write-Output '--- Recent Events (last 5) ---'
    $eventResult = Get-KubectlLines -Arguments @('get', 'events', '-n', $Namespace, '--sort-by=.lastTimestamp', '--no-headers')
    if ($eventResult.Ok -and $eventResult.Lines.Count -gt 0) {
        $eventResult.Lines | Select-Object -Last 5 | ForEach-Object {
            Write-Output ("  {0}" -f $_)
        }
    }
    elseif ($eventResult.Ok) {
        Write-Output '  No events'
    }
    else {
        Write-Output ("[INFO] Recent events unavailable: {0}" -f $eventResult.Error)
    }

    # Service hints preserved from prior script for learner ergonomics
    Write-Output ''
    Write-Output '--- Service Endpoints ---'
    $svcResult = Get-KubectlLines -Arguments @('get', 'svc', '-n', $Namespace, '--no-headers')
    if ($svcResult.Ok) {
        foreach ($line in $svcResult.Lines) {
            $parts = $line -split '\s+'
            if ($parts.Count -lt 5) { continue }
            $name = $parts[0]
            $clusterIp = $parts[2]
            $ports = $parts[4]
            if ($name -eq 'kagent-ui') {
                Write-Output ("[INFO] {0}  {1}  {2}  (port-forward: kubectl port-forward -n {3} svc/{0} {4}:8080)" -f $name, $clusterIp, $ports, $Namespace, $UIPort)
            }
            elseif ($name -eq 'kagent-controller') {
                Write-Output ("[INFO] {0}  {1}  {2}  (port-forward: kubectl port-forward -n {3} svc/{0} {4}:8083)" -f $name, $clusterIp, $ports, $Namespace, $ControllerPort)
            }
            else {
                Write-Output ("[INFO] {0}  {1}  {2}" -f $name, $clusterIp, $ports)
            }
        }
    }
}
else {
    Write-Output (ConvertTo-KagentHealthJson -Result $result)
}

exit [int]$result.exitCode
