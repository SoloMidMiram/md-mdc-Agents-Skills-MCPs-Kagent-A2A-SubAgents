#Requires -Version 5.1
<#
.SYNOPSIS
    Pure parsing and profile-gate evaluation for kagent health checks.
.DESCRIPTION
    Decision logic is intentionally free of kubectl/network so Pester can exercise
    profiles against fixtures. Live collection stays in check-kagent-health.ps1.
#>

Set-StrictMode -Version Latest

$script:SchemaVersion = '1.0'
$script:TargetToolServer = 'kagent-tool-server'
$script:ExpectedDirectTool = 'k8s_get_resources'

function New-HealthGate {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][ValidateSet('pass', 'fail', 'info', 'skip')][string]$Status,
        [Parameter(Mandatory)][string]$Reason
    )
    [pscustomobject]@{
        name   = $Name
        status = $Status
        reason = $Reason
    }
}

function Test-PodReadinessRatio {
    <#
    .SYNOPSIS
        Return $true only for complete positive ratios such as 1/1 or 2/2.
    #>
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Ready)

    if ([string]::IsNullOrWhiteSpace($Ready)) { return $false }
    $parts = $Ready.Trim() -split '/'
    if ($parts.Count -ne 2) { return $false }
    if ($parts[0] -notmatch '^\d+$' -or $parts[1] -notmatch '^\d+$') { return $false }
    $readyCount = [int]$parts[0]
    $totalCount = [int]$parts[1]
    return ($totalCount -gt 0 -and $readyCount -eq $totalCount)
}

function ConvertFrom-KubectlPodLine {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) { return $null }
    $parts = ($Line.Trim() -split '\s+')
    if ($parts.Count -lt 3) {
        return [pscustomobject]@{
            Name      = $null
            Ready     = $null
            Status    = $null
            Restarts  = $null
            Malformed = $true
            Raw       = $Line
        }
    }
    [pscustomobject]@{
        Name      = $parts[0]
        Ready     = $parts[1]
        Status    = $parts[2]
        Restarts  = if ($parts.Count -ge 4) { $parts[3] } else { $null }
        Malformed = $false
        Raw       = $Line
    }
}

function Test-PodHealthy {
    param([Parameter(Mandatory)]$Pod)

    if ($null -eq $Pod -or $Pod.Malformed) { return $false }
    if ($Pod.Status -ne 'Running') { return $false }
    return (Test-PodReadinessRatio -Ready $Pod.Ready)
}

function ConvertFrom-KubectlAgentLine {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) { return $null }
    $parts = ($Line.Trim() -split '\s+')
    # Expected: NAME TYPE RUNTIME READY ACCEPTED
    if ($parts.Count -lt 5) {
        return [pscustomobject]@{
            Name      = $null
            Type      = $null
            Runtime   = $null
            Ready     = $null
            Accepted  = $null
            Malformed = $true
            Raw       = $Line
        }
    }
    [pscustomobject]@{
        Name      = $parts[0]
        Type      = $parts[1]
        Runtime   = $parts[2]
        Ready     = $parts[3]
        Accepted  = $parts[4]
        Malformed = $false
        Raw       = $Line
    }
}

function Test-AgentHealthy {
    param([Parameter(Mandatory)]$Agent)

    if ($null -eq $Agent -or $Agent.Malformed) { return $false }
    if ([string]::IsNullOrWhiteSpace($Agent.Accepted) -or [string]::IsNullOrWhiteSpace($Agent.Ready)) {
        return $false
    }
    return ($Agent.Accepted -eq 'True' -and $Agent.Ready -eq 'True')
}

function ConvertFrom-KubectlRemoteMcpServerLine {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) { return $null }
    $parts = ($Line.Trim() -split '\s+')
    # Expected: NAME PROTOCOL URL ACCEPTED
    if ($parts.Count -lt 4) {
        return [pscustomobject]@{
            Name      = $null
            Protocol  = $null
            Url       = $null
            Accepted  = $null
            Malformed = $true
            Raw       = $Line
        }
    }
    [pscustomobject]@{
        Name      = $parts[0]
        Protocol  = $parts[1]
        Url       = $parts[2]
        Accepted  = $parts[3]
        Malformed = $false
        Raw       = $Line
    }
}

function Get-CardLabGates {
    param(
        [object[]]$Pods = @(),
        [object[]]$Agents = @(),
        [object[]]$RemoteMcpServers = @()
    )

    $gates = [System.Collections.Generic.List[object]]::new()

    $podList = @($Pods | Where-Object { $null -ne $_ })
    if ($podList.Count -eq 0) {
        $gates.Add((New-HealthGate -Name 'pods-ready' -Status 'fail' -Reason 'no pods found'))
    }
    else {
        $unhealthy = @($podList | Where-Object { -not (Test-PodHealthy -Pod $_) })
        $healthyCount = $podList.Count - $unhealthy.Count
        if ($unhealthy.Count -eq 0) {
            $gates.Add((New-HealthGate -Name 'pods-ready' -Status 'pass' -Reason ("{0}/{1} pods ready" -f $healthyCount, $podList.Count)))
        }
        else {
            $names = ($unhealthy | ForEach-Object { $_.Name }) -join ', '
            $gates.Add((New-HealthGate -Name 'pods-ready' -Status 'fail' -Reason ("{0}/{1} pods not ready: {2}" -f $unhealthy.Count, $podList.Count, $names)))
        }
    }

    $agentList = @($Agents | Where-Object { $null -ne $_ })
    if ($agentList.Count -eq 0) {
        $gates.Add((New-HealthGate -Name 'agents-accepted-ready' -Status 'fail' -Reason 'no agents found'))
    }
    else {
        $bad = @($agentList | Where-Object { -not (Test-AgentHealthy -Agent $_) })
        $okCount = $agentList.Count - $bad.Count
        if ($bad.Count -eq 0) {
            $gates.Add((New-HealthGate -Name 'agents-accepted-ready' -Status 'pass' -Reason ("{0}/{1} agents Accepted=True Ready=True" -f $okCount, $agentList.Count)))
        }
        else {
            $names = ($bad | ForEach-Object { $_.Name }) -join ', '
            $gates.Add((New-HealthGate -Name 'agents-accepted-ready' -Status 'fail' -Reason ("{0}/{1} agents not accepted+ready: {2}" -f $bad.Count, $agentList.Count, $names)))
        }
    }

    $serverList = @($RemoteMcpServers | Where-Object { $null -ne $_ })
    foreach ($server in $serverList) {
        if ($server.Malformed) {
            $unknownName = if ([string]::IsNullOrWhiteSpace([string]$server.Name)) { 'unknown' } else { $server.Name }
            $gates.Add((New-HealthGate -Name ("remotemcpserver-{0}" -f $unknownName) -Status 'info' -Reason 'malformed RemoteMCPServer line'))
            continue
        }
        if ($server.Accepted -eq 'True') {
            $gates.Add((New-HealthGate -Name ("remotemcpserver-{0}" -f $server.Name) -Status 'info' -Reason ("Accepted=True url={0}" -f $server.Url)))
        }
        else {
            $gates.Add((New-HealthGate -Name ("remotemcpserver-{0}" -f $server.Name) -Status 'info' -Reason ("Accepted={0} (informational for CardLab)" -f $server.Accepted)))
        }
    }

    return $gates.ToArray()
}

function Test-DirectMcpEvidenceObject {
    <#
    .SYNOPSIS
        Validate sanitized mcp_session_smoke.py JSON. Returns hashtable with Ok/Reason.
    #>
    param(
        [Parameter(Mandatory)]$Evidence,
        [string]$ExpectedTool = $script:ExpectedDirectTool
    )

    if ($null -eq $Evidence) {
        return @{ Ok = $false; Reason = 'direct MCP evidence is null'; ExitCodeHint = 2 }
    }
    if ($Evidence -is [string]) {
        return @{ Ok = $false; Reason = 'direct MCP evidence must be structured JSON object'; ExitCodeHint = 2 }
    }

    $props = @{}
    foreach ($p in $Evidence.PSObject.Properties) { $props[$p.Name] = $p.Value }

    foreach ($required in @('exitCode', 'sessionId', 'toolCallSucceeded', 'tool', 'error')) {
        if (-not $props.ContainsKey($required)) {
            return @{ Ok = $false; Reason = "direct MCP evidence missing field '$required'"; ExitCodeHint = 2 }
        }
    }

    $exitCode = $props['exitCode']
    if ($exitCode -isnot [int] -and $exitCode -isnot [long] -and "$exitCode" -notmatch '^-?\d+$') {
        return @{ Ok = $false; Reason = 'exitCode must be numeric'; ExitCodeHint = 2 }
    }
    if ([int]$exitCode -ne 0) {
        return @{ Ok = $false; Reason = "exitCode is $exitCode (want 0)"; ExitCodeHint = 1 }
    }
    if ("$($props['sessionId'])" -ne 'present') {
        return @{ Ok = $false; Reason = "sessionId must equal 'present' (never a raw id)"; ExitCodeHint = 1 }
    }
    if ($props['toolCallSucceeded'] -ne $true -and "$($props['toolCallSucceeded'])" -ne 'True') {
        return @{ Ok = $false; Reason = 'toolCallSucceeded must be true'; ExitCodeHint = 1 }
    }
    if ("$($props['tool'])" -ne $ExpectedTool) {
        return @{ Ok = $false; Reason = ("tool must be '{0}', got '{1}'" -f $ExpectedTool, $props['tool']); ExitCodeHint = 1 }
    }
    if ($null -ne $props['error']) {
        return @{ Ok = $false; Reason = 'error must be null for a passing direct MCP result'; ExitCodeHint = 1 }
    }

    return @{ Ok = $true; Reason = 'direct MCP evidence validates (session present, toolCallSucceeded)'; ExitCodeHint = 0 }
}

function Test-A2ADispatchEvidenceObject {
    <#
    .SYNOPSIS
        Decide whether structured A2A dispatch evidence proves acceptance/completion.

        Requires schemaVersion 1.0. Nested helper evidence is accepted only when
        helper exit, decision, transport, protocol, and dispatch fields agree.
    #>
    param([Parameter(Mandatory)]$Evidence)

    if ($null -eq $Evidence) {
        return @{ Ok = $false; Reason = 'A2A dispatch evidence is null'; ExitCodeHint = 2 }
    }

    $props = @{}
    foreach ($p in $Evidence.PSObject.Properties) { $props[$p.Name] = $p.Value }

    $schemaVersion = "$($props['schemaVersion'])"
    if ([string]::IsNullOrWhiteSpace($schemaVersion)) {
        return @{ Ok = $false; Reason = 'missing schemaVersion'; ExitCodeHint = 2 }
    }
    if ($schemaVersion -ne '1.0') {
        return @{ Ok = $false; Reason = ("schemaVersion must be '1.0', got '{0}'" -f $schemaVersion); ExitCodeHint = 2 }
    }

    $nestedContract = $props.ContainsKey('action') -or $props.ContainsKey('target') -or
        $props.ContainsKey('transport') -or $props.ContainsKey('protocol') -or
        $props.ContainsKey('dispatch') -or $props.ContainsKey('decision')

    if ($nestedContract) {
        foreach ($required in @('action', 'observedAt', 'target', 'transport', 'protocol', 'dispatch', 'decision', 'helperExit')) {
            if (-not $props.ContainsKey($required) -or $null -eq $props[$required]) {
                return @{ Ok = $false; Reason = "missing required nested evidence field '$required'"; ExitCodeHint = 2 }
            }
        }

        if ("$($props['action'])" -notin @('task', 'both')) {
            return @{ Ok = $false; Reason = "action must be 'task' or 'both' for dispatch evidence"; ExitCodeHint = 2 }
        }
        if ([string]::IsNullOrWhiteSpace("$($props['observedAt'])")) {
            return @{ Ok = $false; Reason = "missing required nested evidence field 'observedAt'"; ExitCodeHint = 2 }
        }

        $maps = @{}
        foreach ($name in @('target', 'transport', 'protocol', 'dispatch', 'decision')) {
            $map = @{}
            foreach ($p in $props[$name].PSObject.Properties) { $map[$p.Name] = $p.Value }
            $maps[$name] = $map
        }
        $target = $maps['target']
        $transport = $maps['transport']
        $protocol = $maps['protocol']
        $dispatch = $maps['dispatch']
        $decision = $maps['decision']

        foreach ($required in @('namespace', 'agent', 'controller', 'endpoint')) {
            if (-not $target.ContainsKey($required) -or [string]::IsNullOrWhiteSpace("$($target[$required])")) {
                return @{ Ok = $false; Reason = "target.$required is required"; ExitCodeHint = 2 }
            }
        }
        foreach ($required in @('succeeded', 'httpStatus', 'error')) {
            if (-not $transport.ContainsKey($required)) {
                return @{ Ok = $false; Reason = "transport.$required is required"; ExitCodeHint = 2 }
            }
        }
        foreach ($required in @('jsonRpc', 'method', 'requestId', 'responseIdMatched', 'error')) {
            if (-not $protocol.ContainsKey($required)) {
                return @{ Ok = $false; Reason = "protocol.$required is required"; ExitCodeHint = 2 }
            }
        }
        foreach ($required in @('accepted', 'taskOrMessageId', 'state', 'responseKind')) {
            if (-not $dispatch.ContainsKey($required)) {
                return @{ Ok = $false; Reason = "dispatch.$required is required"; ExitCodeHint = 2 }
            }
        }
        foreach ($required in @('passed', 'exitCode')) {
            if (-not $decision.ContainsKey($required)) {
                return @{ Ok = $false; Reason = "decision.$required is required"; ExitCodeHint = 2 }
            }
        }

        $helperExit = 0
        $decisionExit = 0
        if (-not [int]::TryParse("$($props['helperExit'])", [ref]$helperExit) -or
            -not [int]::TryParse("$($decision['exitCode'])", [ref]$decisionExit)) {
            return @{ Ok = $false; Reason = 'helperExit and decision.exitCode must be integers'; ExitCodeHint = 2 }
        }
        if ($helperExit -ne $decisionExit) {
            return @{ Ok = $false; Reason = 'helperExit does not match decision.exitCode'; ExitCodeHint = 2 }
        }

        $passed = $decision['passed'] -eq $true -or "$($decision['passed'])" -eq 'True'
        $transportSucceeded = $transport['succeeded'] -eq $true -or "$($transport['succeeded'])" -eq 'True'
        $dispatchAccepted = $dispatch['accepted'] -eq $true -or "$($dispatch['accepted'])" -eq 'True'
        $hasDispatchId = -not [string]::IsNullOrWhiteSpace("$($dispatch['taskOrMessageId'])")
        $hasDispatchState = -not [string]::IsNullOrWhiteSpace("$($dispatch['state'])")
        $hasResponseKind = -not [string]::IsNullOrWhiteSpace("$($dispatch['responseKind'])")

        if ($decisionExit -eq 3) {
            if ($passed -or $transportSucceeded -or $dispatchAccepted -or $hasDispatchId -or $hasDispatchState -or $hasResponseKind) {
                return @{ Ok = $false; Reason = 'transport exit 3 conflicts with decision, transport, or dispatch evidence'; ExitCodeHint = 2 }
            }
            return @{ Ok = $false; Reason = ("A2A transport failure: {0}" -f $transport['error']); ExitCodeHint = 3 }
        }
        if ($decisionExit -eq 2) {
            if ($passed) {
                return @{ Ok = $false; Reason = 'decision.passed conflicts with exit code 2'; ExitCodeHint = 2 }
            }
            return @{ Ok = $false; Reason = 'A2A helper reported invalid input or evidence'; ExitCodeHint = 2 }
        }
        if ($decisionExit -notin @(0, 1)) {
            return @{ Ok = $false; Reason = "unsupported helper exit code $decisionExit"; ExitCodeHint = 2 }
        }
        if ($passed -ne ($decisionExit -eq 0)) {
            return @{ Ok = $false; Reason = 'decision.passed does not agree with decision.exitCode'; ExitCodeHint = 2 }
        }
        if (-not $passed) {
            if (-not $transportSucceeded -or $dispatchAccepted -or $hasDispatchId -or $hasDispatchState -or $hasResponseKind -or
                $null -ne $transport['error'] -or "$($protocol['jsonRpc'])" -ne '2.0' -or
                "$($protocol['method'])" -ne 'message/stream') {
                return @{ Ok = $false; Reason = 'gate exit 1 conflicts with transport, protocol, or dispatch evidence'; ExitCodeHint = 2 }
            }
            return @{ Ok = $false; Reason = 'A2A helper rejected the dispatch'; ExitCodeHint = 1 }
        }

        $httpStatus = 0
        if (-not [int]::TryParse("$($transport['httpStatus'])", [ref]$httpStatus)) {
            return @{ Ok = $false; Reason = 'transport.httpStatus must be an integer'; ExitCodeHint = 2 }
        }
        if (-not $transportSucceeded -or $httpStatus -lt 200 -or $httpStatus -ge 300 -or $null -ne $transport['error']) {
            return @{ Ok = $false; Reason = 'passing decision conflicts with transport evidence'; ExitCodeHint = 2 }
        }
        if ("$($protocol['jsonRpc'])" -ne '2.0' -or "$($protocol['method'])" -ne 'message/stream' -or
            [string]::IsNullOrWhiteSpace("$($protocol['requestId'])") -or
            -not ($protocol['responseIdMatched'] -eq $true -or "$($protocol['responseIdMatched'])" -eq 'True') -or
            $null -ne $protocol['error']) {
            return @{ Ok = $false; Reason = 'passing decision conflicts with protocol evidence'; ExitCodeHint = 2 }
        }
        if (-not $dispatchAccepted -or [string]::IsNullOrWhiteSpace("$($dispatch['taskOrMessageId'])")) {
            return @{ Ok = $false; Reason = 'passing decision lacks accepted dispatch and identifier'; ExitCodeHint = 2 }
        }

        $responseKind = "$($dispatch['responseKind'])"
        $state = "$($dispatch['state'])".ToLowerInvariant()
        if ($responseKind -notin @('status-update', 'task', 'message')) {
            return @{ Ok = $false; Reason = 'dispatch.responseKind is not recognized'; ExitCodeHint = 2 }
        }
        if ($responseKind -eq 'message') {
            if (-not [string]::IsNullOrWhiteSpace($state)) {
                return @{ Ok = $false; Reason = 'message dispatch state must be null or empty'; ExitCodeHint = 2 }
            }
        }
        elseif ($state -notin @('submitted', 'working', 'completed', 'input_required')) {
            return @{ Ok = $false; Reason = 'task/status-update dispatch state is not accepted'; ExitCodeHint = 1 }
        }

        return @{ Ok = $true; Reason = 'A2A helper contract is internally consistent and proves accepted dispatch'; ExitCodeHint = 0 }
    }

    # Transport failures (flat or nested)
    if ($props.ContainsKey('transportError') -and $props['transportError']) {
        return @{ Ok = $false; Reason = ("A2A transport failure: {0}" -f $props['transportError']); ExitCodeHint = 3 }
    }
    if ($props.ContainsKey('httpStatus') -and $props['httpStatus'] -and [int]$props['httpStatus'] -ge 400) {
        return @{ Ok = $false; Reason = ("A2A HTTP {0}" -f $props['httpStatus']); ExitCodeHint = 3 }
    }

    # JSON-RPC errors (flat or nested)
    $jsonRpcError = $null
    if ($props.ContainsKey('jsonRpcError') -and $null -ne $props['jsonRpcError']) {
        $jsonRpcError = $props['jsonRpcError']
    }
    if ($null -ne $jsonRpcError) {
        $code = $null
        $msg = "$jsonRpcError"
        if ($jsonRpcError -is [System.Management.Automation.PSObject] -or $jsonRpcError -is [hashtable]) {
            if ($jsonRpcError.code) { $code = $jsonRpcError.code }
            if ($jsonRpcError.message) { $msg = $jsonRpcError.message }
        }
        if ($code -eq -32601 -or "$msg" -match 'method not found') {
            return @{ Ok = $false; Reason = 'tasks/sendTask or method returned -32601 method not found'; ExitCodeHint = 1 }
        }
        if ($code -eq -32603) {
            return @{ Ok = $false; Reason = ("message/send or stream returned -32603: {0}" -f $msg); ExitCodeHint = 1 }
        }
        return @{ Ok = $false; Reason = ("A2A JSON-RPC error code={0} message={1}" -f $code, $msg); ExitCodeHint = 1 }
    }

    if ($props.ContainsKey('cardOnly') -and ($props['cardOnly'] -eq $true -or "$($props['cardOnly'])" -eq 'True')) {
        return @{ Ok = $false; Reason = 'agent card success alone does not prove A2A dispatch'; ExitCodeHint = 1 }
    }
    if ($props.ContainsKey('probeOnly') -and ($props['probeOnly'] -eq $true -or "$($props['probeOnly'])" -eq 'True')) {
        return @{ Ok = $false; Reason = 'probe completion alone does not prove A2A dispatch'; ExitCodeHint = 1 }
    }
    if ($props.ContainsKey('methodRegistered') -and ($props['methodRegistered'] -eq $true)) {
        return @{ Ok = $false; Reason = 'method registration is not dispatch success'; ExitCodeHint = 1 }
    }

    # Resolve identifier and acceptance flags from flat or nested shapes
    $taskOrMessageId = "$($props['taskOrMessageId'])"
    $state = "$($props['taskState'])".ToLowerInvariant()
    $accepted = $props['accepted'] -eq $true -or "$($props['accepted'])" -eq 'True'
    $completed = $props['completed'] -eq $true -or "$($props['completed'])" -eq 'True'

    if ([string]::IsNullOrWhiteSpace($taskOrMessageId)) {
        if ($accepted -or $completed -or $state -in @('submitted', 'working', 'completed', 'accepted', 'input_required')) {
            return @{ Ok = $false; Reason = 'A2A evidence lacks non-empty taskOrMessageId'; ExitCodeHint = 1 }
        }
        return @{ Ok = $false; Reason = 'A2A evidence does not show accepted/completed task or message'; ExitCodeHint = 1 }
    }

    if ($accepted -or $completed -or $state -in @('submitted', 'working', 'completed', 'accepted', 'input_required')) {
        return @{ Ok = $true; Reason = 'A2A task/message accepted or completed with identifier'; ExitCodeHint = 0 }
    }

    return @{ Ok = $false; Reason = 'A2A evidence does not show accepted/completed task or message'; ExitCodeHint = 1 }
}

function Test-AgentMediatedA2ASection {
    param(
        [Parameter(Mandatory)]$Evidence,
        [string]$ExpectedClusterContext = 'docker-desktop',
        [string]$ExpectedNamespace = 'kagent',
        [string]$ExpectedAgent = 'k8s-a2a-agent',
        [string]$ExpectedControllerOrigin = 'http://127.0.0.1:8083',
        [string]$ExpectedMcpServer = 'kagent-tool-server'
    )

    if ($null -eq $Evidence -or "$($Evidence.schemaVersion)" -ne '1.0' -or "$($Evidence.evidenceKind)" -ne 'agent-mediated-mcp') {
        return @{ Ok = $false; Reason = 'agent-mediated schema 1.0 evidence is required'; ExitCodeHint = 2; TaskId = '' }
    }
    if ($null -eq $Evidence.target -or $null -eq $Evidence.a2a) {
        return @{ Ok = $false; Reason = 'target and a2a objects are required'; ExitCodeHint = 2; TaskId = '' }
    }
    $target = $Evidence.target
    $a2a = $Evidence.a2a
    try {
        $controllerUri = [uri]"$($target.controller)"
        $expectedUri = [uri]$ExpectedControllerOrigin
        $controllerOrigin = ("{0}://{1}" -f $controllerUri.Scheme, $controllerUri.Authority).ToLowerInvariant()
        $expectedOrigin = ("{0}://{1}" -f $expectedUri.Scheme, $expectedUri.Authority).ToLowerInvariant()
    }
    catch {
        return @{ Ok = $false; Reason = 'target.controller is not a valid absolute origin'; ExitCodeHint = 2; TaskId = '' }
    }
    if ("$($target.clusterContext)" -ne $ExpectedClusterContext -or "$($target.namespace)" -ne $ExpectedNamespace -or "$($target.agent)" -ne $ExpectedAgent -or "$($target.mcpServer)" -ne $ExpectedMcpServer -or $controllerOrigin -ne $expectedOrigin) {
        return @{ Ok = $false; Reason = 'agent-mediated A2A target mismatch'; ExitCodeHint = 1; TaskId = '' }
    }
    $taskId = "$($a2a.taskOrMessageId)"
    if ("$($a2a.method)" -ne 'message/stream' -or [string]::IsNullOrWhiteSpace("$($a2a.requestId)") -or [string]::IsNullOrWhiteSpace($taskId)) {
        return @{ Ok = $false; Reason = 'agent-mediated A2A method or identifiers are invalid'; ExitCodeHint = 2; TaskId = $taskId }
    }
    if ("$($a2a.acceptedState)" -notin @('submitted', 'working', 'completed', 'input_required')) {
        return @{ Ok = $false; Reason = 'agent-mediated A2A state is not accepted'; ExitCodeHint = 1; TaskId = $taskId }
    }
    $transport = if ($null -ne $a2a.PSObject.Properties['transport']) { $a2a.transport } else { $null }
    $protocol = if ($null -ne $a2a.PSObject.Properties['protocol']) { $a2a.protocol } else { $null }
    $dispatch = if ($null -ne $a2a.PSObject.Properties['dispatch']) { $a2a.dispatch } else { $null }
    if ($null -eq $transport -or $null -eq $protocol -or $null -eq $dispatch) {
        return @{ Ok = $false; Reason = 'agent-mediated A2A transport, protocol, and dispatch objects are required'; ExitCodeHint = 2; TaskId = $taskId }
    }
    $httpStatus = 0
    if (-not ($transport.succeeded -eq $true -or "$($transport.succeeded)" -eq 'True') -or -not [int]::TryParse("$($transport.httpStatus)", [ref]$httpStatus) -or $httpStatus -lt 200 -or $httpStatus -gt 299) {
        return @{ Ok = $false; Reason = 'agent-mediated A2A transport did not succeed with HTTP 2xx'; ExitCodeHint = 2; TaskId = $taskId }
    }
    $protocolHasError = $null -ne $protocol.PSObject.Properties['error'] -and $null -ne $protocol.error
    if ("$($protocol.jsonRpc)" -ne '2.0' -or "$($protocol.requestId)" -ne "$($a2a.requestId)" -or -not ($protocol.responseIdMatched -eq $true -or "$($protocol.responseIdMatched)" -eq 'True') -or $protocolHasError) {
        return @{ Ok = $false; Reason = 'agent-mediated A2A protocol fields are inconsistent'; ExitCodeHint = 2; TaskId = $taskId }
    }
    if (-not ($dispatch.accepted -eq $true -or "$($dispatch.accepted)" -eq 'True') -or "$($dispatch.taskOrMessageId)" -ne $taskId -or "$($dispatch.state)" -ne "$($a2a.acceptedState)") {
        return @{ Ok = $false; Reason = 'agent-mediated A2A dispatch fields are inconsistent'; ExitCodeHint = 2; TaskId = $taskId }
    }
    return @{ Ok = $true; Reason = 'same-task agent-mediated A2A section validates'; ExitCodeHint = 0; TaskId = $taskId }
}

function Test-AgentMediatedEvidenceObject {
    <#
    .SYNOPSIS
        Validate educational L6 evidence (nested schema 1.0 with freshness/correlation).
    #>
    param(
        [Parameter(Mandatory)]$Evidence,
        [string]$RepoRoot = '',
        [string]$ExpectedClusterContext = 'docker-desktop',
        [string]$ExpectedNamespace = 'kagent',
        [string]$ExpectedAgent = 'k8s-a2a-agent',
        [string]$ExpectedControllerOrigin = 'http://127.0.0.1:8083',
        [string]$ExpectedMcpServer = 'kagent-tool-server',
        [string]$ExpectedTool = 'k8s_get_resources',
        [datetime]$EvaluationTimeUtc = ([datetime]::UtcNow)
    )

    if ($null -eq $Evidence) {
        return @{ Ok = $false; Reason = 'agent-mediated evidence is null'; ExitCodeHint = 2 }
    }

    $props = @{}
    foreach ($p in $Evidence.PSObject.Properties) { $props[$p.Name] = $p.Value }

    if (-not $props.ContainsKey('schemaVersion') -or [string]::IsNullOrWhiteSpace("$($props['schemaVersion'])")) {
        return @{ Ok = $false; Reason = 'missing schemaVersion'; ExitCodeHint = 2 }
    }
    if ("$($props['schemaVersion'])" -ne '1.0') {
        return @{ Ok = $false; Reason = ("schemaVersion must be '1.0', got '{0}'" -f $props['schemaVersion']); ExitCodeHint = 2 }
    }

    $kind = "$($props['evidenceKind'])"
    if ($kind -eq 'direct-mcp-tool-call') {
        return @{ Ok = $false; Reason = 'evidenceKind direct-mcp-tool-call is insufficient for FullMcpExecution'; ExitCodeHint = 1 }
    }
    if ($kind -ne 'agent-mediated-mcp') {
        return @{ Ok = $false; Reason = ("evidenceKind must be agent-mediated-mcp, got '{0}'" -f $kind); ExitCodeHint = 2 }
    }

    if (-not $props.ContainsKey('decision') -or $null -eq $props['decision']) {
        return @{ Ok = $false; Reason = 'missing decision object'; ExitCodeHint = 2 }
    }
    $decision = $props['decision']
    if ($null -eq $decision.PSObject.Properties['passed'] -or $null -eq $decision.PSObject.Properties['exitCode']) {
        return @{ Ok = $false; Reason = 'decision.passed and decision.exitCode are required'; ExitCodeHint = 2 }
    }
    $decisionExit = 0
    if (-not [int]::TryParse("$($decision.exitCode)", [ref]$decisionExit) -or $decisionExit -notin @(0, 1, 2, 3)) {
        return @{ Ok = $false; Reason = 'decision.exitCode must be 0, 1, 2, or 3'; ExitCodeHint = 2 }
    }
    $decisionPassed = $decision.passed -eq $true -or "$($decision.passed)" -eq 'True'
    if ($decisionPassed -ne ($decisionExit -eq 0)) {
        return @{ Ok = $false; Reason = 'decision.passed does not agree with decision.exitCode'; ExitCodeHint = 2 }
    }
    if (-not $props.ContainsKey('success')) {
        return @{ Ok = $false; Reason = 'missing success field'; ExitCodeHint = 2 }
    }
    $successValue = $props['success'] -eq $true -or "$($props['success'])" -eq 'True'
    if ($successValue -ne $decisionPassed) {
        return @{ Ok = $false; Reason = 'success does not agree with decision.passed'; ExitCodeHint = 2 }
    }
    if ($props.ContainsKey('helperExit') -and $null -ne $props['helperExit']) {
        $helperExit = 0
        if (-not [int]::TryParse("$($props['helperExit'])", [ref]$helperExit) -or $helperExit -ne $decisionExit) {
            return @{ Ok = $false; Reason = 'helperExit does not match decision.exitCode'; ExitCodeHint = 2 }
        }
    }
    if ($decisionExit -eq 3) {
        return @{ Ok = $false; Reason = 'agent-mediated evidence collector/transport failure'; ExitCodeHint = 3 }
    }
    if ($decisionExit -eq 2) {
        return @{ Ok = $false; Reason = 'agent-mediated helper reported invalid input/evidence'; ExitCodeHint = 2 }
    }
    if ($decisionExit -eq 1) {
        return @{ Ok = $false; Reason = "$($decision.reason)"; ExitCodeHint = 1 }
    }

    $observedAt = "$($props['observedAt'])"
    if ([string]::IsNullOrWhiteSpace($observedAt)) {
        return @{ Ok = $false; Reason = 'missing observedAt'; ExitCodeHint = 2 }
    }

    $target = $props['target']
    $a2a = $props['a2a']
    $toolInv = $props['toolInvocation']
    $result = $props['result']
    $prov = $props['provenance']
    $decision = $props['decision']

    # Nested schema preferred; map flat aliases when nested absent (legacy fixtures fail closed on missing correlation).
    $agentName = if ($null -ne $target) { "$($target.agent)" } else { "$($props['agentName'])" }
    $agentNs = if ($null -ne $target) { "$($target.namespace)" } else { "$($props['agentNamespace'])" }
    $mcpServer = if ($null -ne $target) { "$($target.mcpServer)" } else { '' }
    $cluster = if ($null -ne $target) { "$($target.clusterContext)" } else { '' }

    $taskId = if ($null -ne $a2a) { "$($a2a.taskOrMessageId)" } else { "$($props['a2aTaskOrMessageId'])" }
    $acceptedState = if ($null -ne $a2a) { "$($a2a.acceptedState)" } else { '' }
    $a2aMethod = if ($null -ne $a2a) { "$($a2a.method)" } else { '' }
    $requestId = if ($null -ne $a2a) { "$($a2a.requestId)" } else { '' }

    if ([string]::IsNullOrWhiteSpace($taskId)) {
        return @{ Ok = $false; Reason = 'missing A2A taskOrMessageId'; ExitCodeHint = 2 }
    }
    if ($null -eq $toolInv) {
        return @{ Ok = $false; Reason = 'missing toolInvocation object'; ExitCodeHint = 2 }
    }
    if ($null -eq $result) {
        return @{ Ok = $false; Reason = 'missing result object'; ExitCodeHint = 2 }
    }
    if ($null -eq $prov) {
        return @{ Ok = $false; Reason = 'missing provenance object'; ExitCodeHint = 2 }
    }

    $controller = if ($null -ne $target) { "$($target.controller)" } else { '' }
    try {
        $controllerUri = [uri]$controller
        $expectedControllerUri = [uri]$ExpectedControllerOrigin
        $controllerOrigin = ("{0}://{1}" -f $controllerUri.Scheme, $controllerUri.Authority).ToLowerInvariant()
        $expectedController = ("{0}://{1}" -f $expectedControllerUri.Scheme, $expectedControllerUri.Authority).ToLowerInvariant()
    }
    catch {
        return @{ Ok = $false; Reason = 'target.controller is not a valid absolute origin'; ExitCodeHint = 2 }
    }
    if ($cluster -ne $ExpectedClusterContext -or $agentNs -ne $ExpectedNamespace -or $agentName -ne $ExpectedAgent -or $mcpServer -ne $ExpectedMcpServer -or $controllerOrigin -ne $expectedController) {
        return @{ Ok = $false; Reason = 'unexpected cluster, namespace, agent, or mcp server'; ExitCodeHint = 1 }
    }
    if ($a2aMethod -ne 'message/stream') {
        return @{ Ok = $false; Reason = 'a2a.method must be message/stream'; ExitCodeHint = 1 }
    }
    if ([string]::IsNullOrWhiteSpace($requestId)) {
        return @{ Ok = $false; Reason = 'missing a2a.requestId'; ExitCodeHint = 2 }
    }
    if ($acceptedState -notin @('submitted', 'working', 'completed', 'input_required')) {
        return @{ Ok = $false; Reason = ("unaccepted a2a.acceptedState '{0}'" -f $acceptedState); ExitCodeHint = 1 }
    }
    $a2aContract = Test-AgentMediatedA2ASection -Evidence $Evidence `
        -ExpectedClusterContext $ExpectedClusterContext `
        -ExpectedNamespace $ExpectedNamespace `
        -ExpectedAgent $ExpectedAgent `
        -ExpectedControllerOrigin $ExpectedControllerOrigin `
        -ExpectedMcpServer $ExpectedMcpServer
    if (-not $a2aContract.Ok) {
        return @{ Ok = $false; Reason = $a2aContract.Reason; ExitCodeHint = $a2aContract.ExitCodeHint }
    }

    $toolObserved = $toolInv.observed -eq $true -or "$($toolInv.observed)" -eq 'True'
    if (-not $toolObserved) {
        return @{ Ok = $false; Reason = 'no observable MCP tool invocation'; ExitCodeHint = 1 }
    }
    $corrId = "$($toolInv.correlatedTaskOrMessageId)"
    if ([string]::IsNullOrWhiteSpace($corrId) -or $corrId -ne $taskId) {
        return @{ Ok = $false; Reason = 'task/trace ID mismatch between dispatch and tool observation'; ExitCodeHint = 1 }
    }
    if ("$($toolInv.server)" -ne $ExpectedMcpServer -or "$($toolInv.tool)" -ne $ExpectedTool) {
        return @{ Ok = $false; Reason = 'unexpected MCP server or tool'; ExitCodeHint = 1 }
    }
    if ($null -eq $toolInv.argumentsSummary -or "$($toolInv.argumentsSummary.resourceType)".ToLowerInvariant() -ne 'pod' -or "$($toolInv.argumentsSummary.namespace)" -ne $ExpectedNamespace) {
        return @{ Ok = $false; Reason = 'unexpected or missing tool arguments'; ExitCodeHint = 1 }
    }
    $srcKind = ''
    if ($null -ne $toolInv.source) { $srcKind = "$($toolInv.source.kind)" }
    if ($srcKind -notin @('protocol-result', 'agent-log', 'controller-log')) {
        return @{ Ok = $false; Reason = 'missing or invalid toolInvocation.source.kind'; ExitCodeHint = 2 }
    }
    $srcReference = if ($null -ne $toolInv.source) { "$($toolInv.source.reference)" } else { '' }
    if ([string]::IsNullOrWhiteSpace($srcReference)) {
        return @{ Ok = $false; Reason = 'missing toolInvocation.source.reference'; ExitCodeHint = 2 }
    }

    $returned = $result.returnedThroughA2A -eq $true -or "$($result.returnedThroughA2A)" -eq 'True'
    if (-not $returned) {
        return @{ Ok = $false; Reason = 'tool result not returned through A2A'; ExitCodeHint = 1 }
    }
    $matched = $result.matched -eq $true -or "$($result.matched)" -eq 'True'
    if (-not $matched) {
        return @{ Ok = $false; Reason = 'Kubernetes cross-check mismatch'; ExitCodeHint = 1 }
    }
    $toolNames = @()
    if ($null -ne $result.toolDerivedResourceNames) {
        $toolNames = @($result.toolDerivedResourceNames | ForEach-Object { "$_" } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    }
    if ($toolNames.Count -eq 0) {
        return @{ Ok = $false; Reason = 'missing tool-derived resource names'; ExitCodeHint = 1 }
    }
    $crossNames = @()
    if ($null -ne $result.crossCheckResourceNames) {
        $crossNames = @($result.crossCheckResourceNames | ForEach-Object { "$_".ToLowerInvariant() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
    }
    $toolNames = @($toolNames | ForEach-Object { $_.ToLowerInvariant() } | Sort-Object -Unique)
    if ($crossNames.Count -eq 0) {
        return @{ Ok = $false; Reason = 'missing Kubernetes cross-check resource names'; ExitCodeHint = 1 }
    }
    $computedMatch = (@($toolNames | Where-Object { $_ -notin $crossNames }).Count -eq 0)
    if (-not $computedMatch -and $matched) {
        return @{ Ok = $false; Reason = 'result.matched contradicts resource-name arrays'; ExitCodeHint = 2 }
    }
    if (-not $computedMatch) {
        return @{ Ok = $false; Reason = 'Kubernetes cross-check resource names do not contain all tool-derived names'; ExitCodeHint = 1 }
    }

    # Check time semantics before source-file correlation so stale/future evidence
    # is classified by its timestamp even when the referenced capture is unavailable.
    $earlyMaxFresh = 0
    $earlyFresh = 0
    if ($null -eq $prov.maxFreshnessSeconds -or -not [int]::TryParse("$($prov.maxFreshnessSeconds)", [ref]$earlyMaxFresh) -or $earlyMaxFresh -ne 900) {
        return @{ Ok = $false; Reason = 'provenance.maxFreshnessSeconds must equal 900'; ExitCodeHint = 2 }
    }
    if ($null -eq $prov.freshnessSeconds -or -not [int]::TryParse("$($prov.freshnessSeconds)", [ref]$earlyFresh) -or $earlyFresh -lt 0) {
        return @{ Ok = $false; Reason = 'provenance.freshnessSeconds must be a non-negative integer'; ExitCodeHint = 2 }
    }
    try {
        $earlyObs = [datetime]::Parse($observedAt, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
    }
    catch {
        return @{ Ok = $false; Reason = 'observedAt is not a valid timestamp'; ExitCodeHint = 2 }
    }
    $earlyAge = ($EvaluationTimeUtc.ToUniversalTime() - $earlyObs.ToUniversalTime()).TotalSeconds
    if ($earlyAge -lt -120) {
        return @{ Ok = $false; Reason = 'observedAt is too far in the future'; ExitCodeHint = 1 }
    }
    $earlyComputed = [math]::Max(0, [math]::Floor($earlyAge))
    if ([math]::Abs($earlyComputed - $earlyFresh) -gt 5) {
        return @{ Ok = $false; Reason = 'reported freshnessSeconds does not match observedAt'; ExitCodeHint = 2 }
    }
    if ($earlyComputed -gt $earlyMaxFresh) {
        return @{ Ok = $false; Reason = ("stale evidence age={0}s max={1}s" -f [int]$earlyComputed, $earlyMaxFresh); ExitCodeHint = 1 }
    }

    $srcPath = "$($prov.sourceEvidencePath)"
    if ([string]::IsNullOrWhiteSpace($srcPath)) {
        $srcPath = "$($props['sourceEvidencePath'])"
    }
    if ([string]::IsNullOrWhiteSpace($srcPath)) {
        return @{ Ok = $false; Reason = 'missing sourceEvidencePath'; ExitCodeHint = 2 }
    }
    if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
        $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    }
    if ([IO.Path]::IsPathRooted($srcPath)) {
        return @{ Ok = $false; Reason = 'sourceEvidencePath must be repository-relative'; ExitCodeHint = 2 }
    }
    $repoFull = [IO.Path]::GetFullPath($RepoRoot).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $fullSrc = [IO.Path]::GetFullPath((Join-Path $repoFull ($srcPath -replace '/', [IO.Path]::DirectorySeparatorChar)))
    $repoPrefix = $repoFull + [IO.Path]::DirectorySeparatorChar
    if (-not $fullSrc.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        return @{ Ok = $false; Reason = 'sourceEvidencePath escapes repository root'; ExitCodeHint = 2 }
    }
    if (-not (Test-Path -LiteralPath $fullSrc)) {
        return @{ Ok = $false; Reason = ("sourceEvidencePath does not exist: {0}" -f $srcPath); ExitCodeHint = 2 }
    }
    try {
        $fullSrc = (Resolve-Path -LiteralPath $fullSrc -ErrorAction Stop).Path
    }
    catch {
        return @{ Ok = $false; Reason = ("sourceEvidencePath cannot be resolved: {0}" -f $srcPath); ExitCodeHint = 2 }
    }
    if (-not $fullSrc.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        return @{ Ok = $false; Reason = 'resolved sourceEvidencePath escapes repository root'; ExitCodeHint = 2 }
    }
    try {
        $sourceEvidence = Get-Content -LiteralPath $fullSrc -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        return @{ Ok = $false; Reason = ("sourceEvidencePath is not valid JSON: {0}" -f $_.Exception.Message); ExitCodeHint = 2 }
    }
    if ("$($sourceEvidence.schemaVersion)" -ne '1.0' -or "$($sourceEvidence.evidenceKind)" -ne 'agent-mediated-mcp') {
        return @{ Ok = $false; Reason = 'source evidence schema or kind mismatch'; ExitCodeHint = 2 }
    }
    try {
        $sourceObservedAt = [datetime]::Parse("$($sourceEvidence.observedAt)", $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
    }
    catch {
        return @{ Ok = $false; Reason = 'source evidence observedAt is not a valid timestamp'; ExitCodeHint = 2 }
    }
    if ([math]::Abs(($sourceObservedAt.ToUniversalTime() - $earlyObs.ToUniversalTime()).TotalMilliseconds) -gt 1) {
        return @{ Ok = $false; Reason = 'source evidence observedAt does not match outer evidence'; ExitCodeHint = 2 }
    }
    if ("$($sourceEvidence.taskOrMessageId)" -ne $taskId) {
        return @{ Ok = $false; Reason = 'source evidence task ID does not match outer evidence'; ExitCodeHint = 2 }
    }
    if ("$($sourceEvidence.requestId)" -ne $requestId) {
        return @{ Ok = $false; Reason = 'source evidence request ID does not match outer evidence'; ExitCodeHint = 2 }
    }
    if (-not ($sourceEvidence.toolObserved -eq $true -or "$($sourceEvidence.toolObserved)" -eq 'True') -or "$($sourceEvidence.sourceKind)" -ne $srcKind) {
        return @{ Ok = $false; Reason = 'source evidence tool observation does not match'; ExitCodeHint = 2 }
    }
    $sourceTarget = $sourceEvidence.target
    if ($null -eq $sourceTarget -or "$($sourceTarget.clusterContext)" -ne $cluster -or "$($sourceTarget.namespace)" -ne $agentNs -or "$($sourceTarget.agent)" -ne $agentName -or ("$($sourceTarget.controller)").ToLowerInvariant() -ne $controllerOrigin -or "$($sourceTarget.mcpServer)" -ne $mcpServer) {
        return @{ Ok = $false; Reason = 'source evidence target does not match outer evidence'; ExitCodeHint = 2 }
    }
    $sourceTool = $sourceEvidence.toolEvidence
    if ($null -eq $sourceTool -or "$($sourceTool.kind)" -ne $srcKind -or "$($sourceTool.taskOrMessageId)" -ne $taskId -or "$($sourceTool.server)" -ne $ExpectedMcpServer -or "$($sourceTool.tool)" -ne $ExpectedTool -or "$($sourceTool.reference)" -ne $srcReference) {
        return @{ Ok = $false; Reason = 'source evidence tool marker does not match outer evidence'; ExitCodeHint = 2 }
    }
    if ($null -eq $sourceTool.argumentsSummary -or "$($sourceTool.argumentsSummary.resourceType)".ToLowerInvariant() -ne 'pod' -or "$($sourceTool.argumentsSummary.namespace)" -ne $ExpectedNamespace) {
        return @{ Ok = $false; Reason = 'source evidence tool arguments do not match'; ExitCodeHint = 2 }
    }
    if ($srcKind -in @('agent-log', 'controller-log')) {
        $line = "$($sourceTool.sanitizedLine)"
        $expectedDigest = "$($sourceTool.sha256)".ToLowerInvariant()
        if ([string]::IsNullOrWhiteSpace($line) -or [string]::IsNullOrWhiteSpace($expectedDigest)) {
            return @{ Ok = $false; Reason = 'log source proof lacks sanitized line or digest'; ExitCodeHint = 2 }
        }
        $sha = [Security.Cryptography.SHA256]::Create()
        try {
            $actualDigest = -join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($line)) | ForEach-Object { $_.ToString('x2') })
        }
        finally { $sha.Dispose() }
        if ($actualDigest -ne $expectedDigest -or $srcReference -ne ("log:sha256:{0}" -f $expectedDigest.Substring(0, 16))) {
            return @{ Ok = $false; Reason = 'log source proof digest mismatch'; ExitCodeHint = 2 }
        }
    }
    elseif ($srcKind -eq 'protocol-result') {
        $eventIndex = 0
        $partIndex = 0
        if (-not [int]::TryParse("$($sourceTool.eventIndex)", [ref]$eventIndex) -or -not [int]::TryParse("$($sourceTool.partIndex)", [ref]$partIndex) -or $eventIndex -lt 0 -or $partIndex -lt 0) {
            return @{ Ok = $false; Reason = 'protocol source proof lacks valid event/part indexes'; ExitCodeHint = 2 }
        }
    }
    $sourceResult = $sourceEvidence.resultEvidence
    if ($null -eq $sourceResult) {
        return @{ Ok = $false; Reason = 'source evidence lacks resultEvidence'; ExitCodeHint = 2 }
    }
    $sourceToolNames = @($sourceResult.toolDerivedResourceNames | ForEach-Object { ("$_").ToLowerInvariant() } | Sort-Object -Unique)
    $sourceCrossNames = @($sourceResult.crossCheckResourceNames | ForEach-Object { ("$_").ToLowerInvariant() } | Sort-Object -Unique)
    if (($sourceToolNames -join "`n") -ne ($toolNames -join "`n") -or ($sourceCrossNames -join "`n") -ne ($crossNames -join "`n") -or -not ($sourceResult.returnedThroughA2A -eq $true -or "$($sourceResult.returnedThroughA2A)" -eq 'True') -or -not ($sourceResult.matched -eq $true -or "$($sourceResult.matched)" -eq 'True')) {
        return @{ Ok = $false; Reason = 'source evidence result does not match outer evidence'; ExitCodeHint = 2 }
    }

    $targetBound = $prov.targetBound -eq $true -or "$($prov.targetBound)" -eq 'True'
    $corrOk = $prov.taskTraceCorrelated -eq $true -or "$($prov.taskTraceCorrelated)" -eq 'True'
    if (-not $targetBound) {
        return @{ Ok = $false; Reason = 'provenance.targetBound must be true'; ExitCodeHint = 1 }
    }
    if (-not $corrOk) {
        return @{ Ok = $false; Reason = 'provenance.taskTraceCorrelated must be true'; ExitCodeHint = 1 }
    }

    if ($null -ne $decision) {
        $decPass = $decision.passed -eq $true -or "$($decision.passed)" -eq 'True'
        $decExit = 0
        if ($null -ne $decision.exitCode -and "$($decision.exitCode)" -ne '') {
            $decExit = [int]$decision.exitCode
        }
        if ($decPass -and $decExit -ne 0) {
            return @{ Ok = $false; Reason = 'helper exit/decision mismatch'; ExitCodeHint = 2 }
        }
        if (-not $decPass) {
            return @{ Ok = $false; Reason = 'decision.passed is false'; ExitCodeHint = 1 }
        }
    }

    $success = $props['success']
    if ($null -ne $success -and -not ($success -eq $true -or "$success" -eq 'True')) {
        return @{ Ok = $false; Reason = 'success must be true when present'; ExitCodeHint = 1 }
    }

    return @{ Ok = $true; Reason = 'agent-mediated evidence contract validates'; ExitCodeHint = 0 }
}

function Get-TargetToolServerAccepted {
    param(
        [object[]]$RemoteMcpServers = @(),
        [string]$TargetName = $script:TargetToolServer
    )

    $match = @($RemoteMcpServers | Where-Object { $_ -and -not $_.Malformed -and $_.Name -eq $TargetName })
    if ($match.Count -eq 0) { return $false }
    return ($match[0].Accepted -eq 'True')
}

function New-KagentHealthResult {
    param(
        [Parameter(Mandatory)][string]$Profile,
        [Parameter(Mandatory)][object[]]$Gates,
        [string[]]$Proves = @(),
        [string[]]$DoesNotProve = @(),
        [int]$ForcedExitCode = -1,
        [datetime]$ObservedAt = ([datetime]::UtcNow)
    )

    # Flatten one level so a returned Object[] is not nested inside another object[].
    $gateList = @($Gates | ForEach-Object { $_ })
    $failed = @($gateList | Where-Object { $_.status -eq 'fail' })
    $passed = ($failed.Count -eq 0)
    $exitCode = if ($ForcedExitCode -ge 0) { $ForcedExitCode } elseif ($passed) { 0 } else { 1 }

    [pscustomobject]@{
        schemaVersion = $script:SchemaVersion
        profile       = $Profile
        passed        = [bool]$passed
        exitCode      = $exitCode
        observedAt    = $ObservedAt.ToString('o')
        gates         = $gateList
        proves        = @($Proves | ForEach-Object { $_ })
        doesNotProve  = @($DoesNotProve | ForEach-Object { $_ })
    }
}

function Invoke-KagentHealthProfile {
    <#
    .SYNOPSIS
        Evaluate a named profile against parsed cluster state and optional evidence.
    .OUTPUTS
        Structured health result object.
    #>
    param(
        [Parameter(Mandatory)]
        [ValidateSet('CardLab', 'DirectMcpServer', 'A2ADispatch', 'FullMcpExecution')]
        [string]$Profile,

        [object[]]$Pods = @(),
        [object[]]$Agents = @(),
        [object[]]$RemoteMcpServers = @(),

        $DirectMcpEvidence = $null,
        $A2ADispatchEvidence = $null,
        $AgentMediatedEvidence = $null,

        [switch]$DirectMcpEvidenceRequired,
        [switch]$A2ADispatchEvidenceRequired,
        [switch]$AgentMediatedEvidenceRequired,

        [string]$ExpectedDirectTool = $script:ExpectedDirectTool,
        [string]$TargetToolServer = $script:TargetToolServer,
        [string]$ExpectedClusterContext = 'docker-desktop',
        [string]$ExpectedAgentNamespace = 'kagent',
        [string]$ExpectedAgentName = 'k8s-a2a-agent',
        [string]$ExpectedControllerOrigin = 'http://127.0.0.1:8083',
        [datetime]$EvaluationTimeUtc = ([datetime]::UtcNow)
    )

    $cardGates = @(Get-CardLabGates -Pods $Pods -Agents $Agents -RemoteMcpServers $RemoteMcpServers)
    $cardFailed = @($cardGates | Where-Object { $_.status -eq 'fail' })

    switch ($Profile) {
        'CardLab' {
            return New-KagentHealthResult -Profile $Profile -Gates $cardGates `
                -Proves @('CardLab readiness (pods + accepted/ready agents)') `
                -DoesNotProve @(
                'L4 A2A dispatch',
                'L5 RemoteMCPServer acceptance as tool execution',
                'L6 agent-mediated tool invocation',
                'direct MCP tool invocation'
            )
        }

        'DirectMcpServer' {
            $gates = [System.Collections.Generic.List[object]]::new()
            foreach ($g in $cardGates) { $gates.Add($g) }

            $accepted = Get-TargetToolServerAccepted -RemoteMcpServers $RemoteMcpServers -TargetName $TargetToolServer
            if ($accepted) {
                $gates.Add((New-HealthGate -Name 'tool-server-accepted' -Status 'pass' -Reason ("{0} Accepted=True" -f $TargetToolServer)))
            }
            else {
                $gates.Add((New-HealthGate -Name 'tool-server-accepted' -Status 'fail' -Reason ("{0} is not Accepted=True" -f $TargetToolServer)))
            }

            $forced = -1
            if ($null -eq $DirectMcpEvidence) {
                if ($DirectMcpEvidenceRequired) {
                    $gates.Add((New-HealthGate -Name 'direct-mcp-tool-call' -Status 'fail' -Reason 'DirectMcpResultPath is required for DirectMcpServer'))
                    $forced = 2
                }
                else {
                    $gates.Add((New-HealthGate -Name 'direct-mcp-tool-call' -Status 'fail' -Reason 'direct MCP evidence not provided'))
                }
            }
            else {
                $check = Test-DirectMcpEvidenceObject -Evidence $DirectMcpEvidence -ExpectedTool $ExpectedDirectTool
                $status = if ($check.Ok) { 'pass' } else { 'fail' }
                $gates.Add((New-HealthGate -Name 'direct-mcp-tool-call' -Status $status -Reason $check.Reason))
                if (-not $check.Ok -and $check.ExitCodeHint -eq 2) { $forced = 2 }
            }

            return New-KagentHealthResult -Profile $Profile -Gates $gates.ToArray() -ForcedExitCode $forced `
                -Proves @('Supplied direct MCP smoke evidence and current target-acceptance gates') `
                -DoesNotProve @(
                'L4 A2A dispatch',
                'L6 agent-mediated tool invocation',
                'evidence freshness or target provenance beyond the supplied record',
                'Direct MCP success does not prove L4 or L6.'
            )
        }

        'A2ADispatch' {
            $gates = [System.Collections.Generic.List[object]]::new()
            foreach ($g in $cardGates) { $gates.Add($g) }

            $forced = -1
            if ($null -eq $A2ADispatchEvidence) {
                if ($A2ADispatchEvidenceRequired) {
                    $gates.Add((New-HealthGate -Name 'a2a-dispatch' -Status 'fail' -Reason 'A2A dispatch evidence missing'))
                    $forced = 2
                }
                else {
                    $gates.Add((New-HealthGate -Name 'a2a-dispatch' -Status 'fail' -Reason 'A2A dispatch evidence not provided'))
                }
            }
            else {
                $check = Test-A2ADispatchEvidenceObject -Evidence $A2ADispatchEvidence
                $status = if ($check.Ok) { 'pass' } else { 'fail' }
                $gates.Add((New-HealthGate -Name 'a2a-dispatch' -Status $status -Reason $check.Reason))
                if (-not $check.Ok) {
                    if ($check.ExitCodeHint -eq 3) { $forced = 3 }
                    elseif ($check.ExitCodeHint -eq 2) { $forced = 2 }
                }
            }

            $proves = @()
            $doesNot = @(
                'L6 agent-mediated tool invocation',
                'provenance beyond schemaVersion and helper target binding'
            )
            $a2aGate = $gates | Where-Object { $_.name -eq 'a2a-dispatch' } | Select-Object -First 1
            if ($a2aGate -and $a2aGate.status -eq 'pass' -and $cardFailed.Count -eq 0) {
                $proves = @('A2A dispatch evidence gate satisfied')
            }
            else {
                $doesNot = @('L4 A2A dispatch', 'L6 agent-mediated tool invocation') + $doesNot | Select-Object -Unique
            }

            return New-KagentHealthResult -Profile $Profile -Gates $gates.ToArray() -ForcedExitCode $forced `
                -Proves $proves -DoesNotProve $doesNot
        }

        'FullMcpExecution' {
            $gates = [System.Collections.Generic.List[object]]::new()
            foreach ($g in $cardGates) { $gates.Add($g) }

            $forced = -1

            # FullMcpExecution derives its A2A gate from the same Phase 5E task.
            if ($null -ne $AgentMediatedEvidence) {
                $embeddedA2A = Test-AgentMediatedA2ASection -Evidence $AgentMediatedEvidence `
                    -ExpectedClusterContext $ExpectedClusterContext `
                    -ExpectedNamespace $ExpectedAgentNamespace `
                    -ExpectedAgent $ExpectedAgentName `
                    -ExpectedControllerOrigin $ExpectedControllerOrigin `
                    -ExpectedMcpServer $TargetToolServer
                $a2aStatus = if ($embeddedA2A.Ok) { 'pass' } else { 'fail' }
                $a2aReason = $embeddedA2A.Reason
                if ($null -ne $A2ADispatchEvidence) {
                    $separateA2A = Test-A2ADispatchEvidenceObject -Evidence $A2ADispatchEvidence
                    $separateId = ''
                    if ($null -ne $A2ADispatchEvidence.PSObject.Properties['taskOrMessageId']) {
                        $separateId = "$($A2ADispatchEvidence.taskOrMessageId)"
                    }
                    $separateDispatch = if ($null -ne $A2ADispatchEvidence.PSObject.Properties['dispatch']) { $A2ADispatchEvidence.dispatch } else { $null }
                    if ([string]::IsNullOrWhiteSpace($separateId) -and $null -ne $separateDispatch -and $null -ne $separateDispatch.PSObject.Properties['taskOrMessageId']) {
                        $separateId = "$($separateDispatch.taskOrMessageId)"
                    }
                    if (-not $separateA2A.Ok) {
                        $a2aStatus = 'fail'
                        $a2aReason = $separateA2A.Reason
                    }
                    elseif ($embeddedA2A.Ok -and $separateId -ne $embeddedA2A.TaskId) {
                        $a2aStatus = 'fail'
                        $a2aReason = 'separate A2A evidence task ID does not match Phase 5E task ID'
                        $forced = 2
                    }
                }
                $gates.Add((New-HealthGate -Name 'a2a-dispatch' -Status $a2aStatus -Reason $a2aReason))
                if (-not $embeddedA2A.Ok -and $embeddedA2A.ExitCodeHint -eq 2) { $forced = 2 }
            }
            elseif ($null -ne $A2ADispatchEvidence) {
                $a2a = Test-A2ADispatchEvidenceObject -Evidence $A2ADispatchEvidence
                $gates.Add((New-HealthGate -Name 'a2a-dispatch' -Status $(if ($a2a.Ok) { 'pass' } else { 'fail' }) -Reason $a2a.Reason))
                if (-not $a2a.Ok -and $a2a.ExitCodeHint -eq 3) { $forced = 3 }
                elseif (-not $a2a.Ok -and $a2a.ExitCodeHint -eq 2) { $forced = 2 }
            }
            else {
                $gates.Add((New-HealthGate -Name 'a2a-dispatch' -Status 'fail' -Reason 'agent-mediated evidence with embedded A2A task is required'))
                if ($A2ADispatchEvidenceRequired) { $forced = 2 }
            }

            $accepted = Get-TargetToolServerAccepted -RemoteMcpServers $RemoteMcpServers -TargetName $TargetToolServer
            $gates.Add((New-HealthGate -Name 'tool-server-accepted' -Status $(if ($accepted) { 'pass' } else { 'fail' }) `
                    -Reason $(if ($accepted) { "$TargetToolServer Accepted=True" } else { "$TargetToolServer is not Accepted=True" })))

            # Reject direct-MCP-only shortcut explicitly when provided without agent-mediated evidence
            if ($null -ne $DirectMcpEvidence -and $null -eq $AgentMediatedEvidence) {
                $gates.Add((New-HealthGate -Name 'agent-mediated-tool' -Status 'fail' `
                        -Reason 'direct MCP evidence alone is insufficient for FullMcpExecution'))
            }
            elseif ($null -eq $AgentMediatedEvidence) {
                $gates.Add((New-HealthGate -Name 'agent-mediated-tool' -Status 'fail' `
                        -Reason 'agent-mediated MCP evidence required (task -> agent -> tool -> result)'))
                if ($AgentMediatedEvidenceRequired) { $forced = 2 }
            }
            else {
                $agentEv = Test-AgentMediatedEvidenceObject -Evidence $AgentMediatedEvidence `
                    -ExpectedClusterContext $ExpectedClusterContext `
                    -ExpectedNamespace $ExpectedAgentNamespace `
                    -ExpectedAgent $ExpectedAgentName `
                    -ExpectedControllerOrigin $ExpectedControllerOrigin `
                    -ExpectedMcpServer $TargetToolServer `
                    -ExpectedTool $ExpectedDirectTool `
                    -EvaluationTimeUtc $EvaluationTimeUtc
                $gates.Add((New-HealthGate -Name 'agent-mediated-tool' -Status $(if ($agentEv.Ok) { 'pass' } else { 'fail' }) -Reason $agentEv.Reason))
                if (-not $agentEv.Ok -and $agentEv.ExitCodeHint -eq 3) { $forced = 3 }
                elseif (-not $agentEv.Ok -and $agentEv.ExitCodeHint -eq 2) { $forced = 2 }
            }

            $proves = @()
            $allPass = (@($gates | Where-Object { $_.status -eq 'fail' }).Count -eq 0)
            if ($allPass) {
                $proves = @('Full MCP educational evidence contract satisfied')
            }

            return New-KagentHealthResult -Profile $Profile -Gates $gates.ToArray() -ForcedExitCode $forced `
                -Proves $proves `
                -DoesNotProve @(
                'direct MCP phase 5B output as L6',
                'RemoteMCPServer Accepted=True as tool invocation',
                'agent Accepted=True as tool invocation',
                'automatic L6 promotion without correlated source/trace review'
            )
        }
    }
}

function Format-KagentHealthHuman {
    param([Parameter(Mandatory)]$Result)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add(('=' * 60))
    $lines.Add(("kagent Health Check  profile={0}" -f $Result.profile))
    $lines.Add(("observedAt(UTC)={0}" -f $Result.observedAt))
    $lines.Add(('=' * 60))
    foreach ($gate in @($Result.gates)) {
        if ($null -eq $gate -or $null -eq $gate.PSObject.Properties['name']) { continue }
        $status = [string]$gate.status
        $tag = switch ($status) {
            'pass' { '[PASS]' }
            'fail' { '[FAIL]' }
            'info' { '[INFO]' }
            default { '[SKIP]' }
        }
        $lines.Add(("{0} {1}: {2}" -f $tag, [string]$gate.name, [string]$gate.reason))
    }
    $lines.Add('')
    if ($Result.passed) {
        $lines.Add('RESULT: PROFILE PASSED')
    }
    else {
        $lines.Add('RESULT: PROFILE FAILED')
    }
    if (@($Result.proves).Count -gt 0) {
        $lines.Add(('Proves: {0}' -f (($Result.proves) -join '; ')))
    }
    if (@($Result.doesNotProve).Count -gt 0) {
        $lines.Add(('Does not prove: {0}' -f (($Result.doesNotProve) -join '; ')))
    }
    if ($Result.profile -eq 'DirectMcpServer') {
        $lines.Add('Direct MCP success does not prove L4 or L6.')
    }
    $lines.Add(("exitCode={0}" -f $Result.exitCode))
    $lines.Add(('=' * 60))
    return ($lines -join [Environment]::NewLine)
}

function ConvertTo-KagentHealthJson {
    param([Parameter(Mandatory)]$Result)

    # Build a clean hashtable tree for ConvertTo-Json stability.
    $obj = [ordered]@{
        schemaVersion = $Result.schemaVersion
        profile       = $Result.profile
        passed        = [bool]$Result.passed
        exitCode      = [int]$Result.exitCode
        observedAt    = $Result.observedAt
        gates         = @($Result.gates | ForEach-Object {
                [ordered]@{ name = $_.name; status = $_.status; reason = $_.reason }
            })
        proves        = @($Result.proves)
        doesNotProve  = @($Result.doesNotProve)
    }
    return ($obj | ConvertTo-Json -Depth 6)
}

Export-ModuleMember -Function @(
    'New-HealthGate',
    'Test-PodReadinessRatio',
    'ConvertFrom-KubectlPodLine',
    'Test-PodHealthy',
    'ConvertFrom-KubectlAgentLine',
    'Test-AgentHealthy',
    'ConvertFrom-KubectlRemoteMcpServerLine',
    'Get-CardLabGates',
    'Test-DirectMcpEvidenceObject',
    'Test-A2ADispatchEvidenceObject',
    'Test-AgentMediatedEvidenceObject',
    'Get-TargetToolServerAccepted',
    'New-KagentHealthResult',
    'Invoke-KagentHealthProfile',
    'Format-KagentHealthHuman',
    'ConvertTo-KagentHealthJson'
)
