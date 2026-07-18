# Pester tests for scripts/kagent/KagentHealth.psm1
# Written for Pester 3.x operators (Should Be / Should Match) so they run on the
# repository baseline Pester 3.4.0. Pester 5 compatibility is reported separately.

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$modulePath = Join-Path $repoRoot 'scripts\kagent\KagentHealth.psm1'
Import-Module $modulePath -Force

function New-ValidA2ADispatchEvidence {
    return [pscustomobject]@{
        schemaVersion = '1.0'
        action        = 'task'
        observedAt    = '2026-07-17T12:00:00Z'
        target        = [pscustomobject]@{
            namespace = 'kagent'; agent = 'k8s-a2a-agent'
            controller = 'http://127.0.0.1:8083'; endpoint = '/api/a2a/kagent/k8s-a2a-agent'
        }
        transport     = [pscustomobject]@{ succeeded = $true; httpStatus = 200; errorKind = $null; error = $null }
        protocol      = [pscustomobject]@{
            jsonRpc = '2.0'; method = 'message/stream'; requestId = 'request-fixture-1'
            responseIdMatched = $true; error = $null
        }
        dispatch      = [pscustomobject]@{
            accepted = $true; taskOrMessageId = 'task-nested-1'
            state = 'completed'; responseKind = 'task'
        }
        decision      = [pscustomobject]@{ passed = $true; exitCode = 0; reason = 'ok' }
        helperExit    = 0
    }
}

Describe 'Pod readiness parsing' {
    It 'accepts 1/1' {
        Test-PodReadinessRatio -Ready '1/1' | Should Be $true
    }
    It 'accepts 2/2' {
        Test-PodReadinessRatio -Ready '2/2' | Should Be $true
    }
    It 'rejects 0/1' {
        Test-PodReadinessRatio -Ready '0/1' | Should Be $false
    }
    It 'rejects 1/2' {
        Test-PodReadinessRatio -Ready '1/2' | Should Be $false
    }
    It 'rejects 0/0' {
        Test-PodReadinessRatio -Ready '0/0' | Should Be $false
    }
    It 'rejects malformed readiness' {
        Test-PodReadinessRatio -Ready 'abc' | Should Be $false
    }
    It 'rejects non-Running pod' {
        $pod = ConvertFrom-KubectlPodLine -Line 'x 1/1 CrashLoopBackOff 1'
        Test-PodHealthy -Pod $pod | Should Be $false
    }
}

Describe 'Agent parsing' {
    It 'passes Accepted=True Ready=True' {
        $a = ConvertFrom-KubectlAgentLine -Line 'demo Declarative ADK True True'
        Test-AgentHealthy -Agent $a | Should Be $true
    }
    It 'fails Accepted=False' {
        $a = ConvertFrom-KubectlAgentLine -Line 'demo Declarative ADK True False'
        Test-AgentHealthy -Agent $a | Should Be $false
    }
    It 'fails Ready=False' {
        $a = ConvertFrom-KubectlAgentLine -Line 'demo Declarative ADK False True'
        Test-AgentHealthy -Agent $a | Should Be $false
    }
    It 'fails missing/malformed condition' {
        $a = ConvertFrom-KubectlAgentLine -Line 'demo only'
        Test-AgentHealthy -Agent $a | Should Be $false
        $a.Malformed | Should Be $true
    }
}

Describe 'CardLab profile' {
    $pods = @(
        (ConvertFrom-KubectlPodLine -Line 'p1 1/1 Running 0'),
        (ConvertFrom-KubectlPodLine -Line 'p2 2/2 Running 0')
    )
    $agents = @(
        (ConvertFrom-KubectlAgentLine -Line 'a1 Declarative ADK True True')
    )
    $servers = @(
        (ConvertFrom-KubectlRemoteMcpServerLine -Line 'kagent-tool-server STREAMABLE_HTTP http://x True'),
        (ConvertFrom-KubectlRemoteMcpServerLine -Line 'kagent-grafana-mcp STREAMABLE_HTTP http://y False')
    )

    It 'passes healthy pods and agents' {
        $r = Invoke-KagentHealthProfile -Profile CardLab -Pods $pods -Agents $agents -RemoteMcpServers $servers
        $r.passed | Should Be $true
        $r.exitCode | Should Be 0
    }

    It 'treats unrelated RemoteMCPServer Accepted=False as informational' {
        $r = Invoke-KagentHealthProfile -Profile CardLab -Pods $pods -Agents $agents -RemoteMcpServers $servers
        $info = @($r.gates | Where-Object { $_.name -eq 'remotemcpserver-kagent-grafana-mcp' })
        $info.Count | Should Be 1
        $info[0].status | Should Be 'info'
        $r.passed | Should Be $true
    }

    It 'fails on pod failure with exit 1' {
        $badPods = @((ConvertFrom-KubectlPodLine -Line 'p1 0/1 Running 0'))
        $r = Invoke-KagentHealthProfile -Profile CardLab -Pods $badPods -Agents $agents
        $r.passed | Should Be $false
        $r.exitCode | Should Be 1
    }

    It 'fails on agent failure with exit 1' {
        $badAgents = @((ConvertFrom-KubectlAgentLine -Line 'a1 Declarative ADK False False'))
        $r = Invoke-KagentHealthProfile -Profile CardLab -Pods $pods -Agents $badAgents
        $r.passed | Should Be $false
        $r.exitCode | Should Be 1
    }
}

Describe 'DirectMcpServer profile' {
    $pods = @((ConvertFrom-KubectlPodLine -Line 'p1 1/1 Running 0'))
    $agents = @((ConvertFrom-KubectlAgentLine -Line 'a1 Declarative ADK True True'))
    $servers = @((ConvertFrom-KubectlRemoteMcpServerLine -Line 'kagent-tool-server STREAMABLE_HTTP http://x True'))

    $valid = [pscustomobject]@{
        exitCode          = 0
        sessionId         = 'present'
        toolCallSucceeded = $true
        tool              = 'k8s_get_resources'
        error             = $null
    }

    It 'passes valid phase-5B-shaped result' {
        $r = Invoke-KagentHealthProfile -Profile DirectMcpServer -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -DirectMcpEvidence $valid -DirectMcpEvidenceRequired
        $r.passed | Should Be $true
        $r.exitCode | Should Be 0
    }

    It 'fails initialization-only style result' {
        $initOnly = [pscustomobject]@{
            exitCode          = 0
            sessionId         = 'present'
            toolCallSucceeded = $false
            tool              = 'k8s_get_resources'
            error             = $null
        }
        $r = Invoke-KagentHealthProfile -Profile DirectMcpServer -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -DirectMcpEvidence $initOnly
        $r.passed | Should Be $false
        $r.exitCode | Should Be 1
    }

    It 'fails when session missing' {
        $bad = [pscustomobject]@{
            exitCode          = 0
            sessionId         = 'missing'
            toolCallSucceeded = $true
            tool              = 'k8s_get_resources'
            error             = $null
        }
        $r = Invoke-KagentHealthProfile -Profile DirectMcpServer -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -DirectMcpEvidence $bad
        $r.passed | Should Be $false
    }

    It 'fails wrong tool' {
        $bad = [pscustomobject]@{
            exitCode          = 0
            sessionId         = 'present'
            toolCallSucceeded = $true
            tool              = 'other'
            error             = $null
        }
        $r = Invoke-KagentHealthProfile -Profile DirectMcpServer -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -DirectMcpEvidence $bad
        $r.passed | Should Be $false
    }

    It 'malformed/missing evidence uses exit 2 when required' {
        $r = Invoke-KagentHealthProfile -Profile DirectMcpServer -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -DirectMcpEvidence $null -DirectMcpEvidenceRequired
        $r.exitCode | Should Be 2

        $missingError = [pscustomobject]@{
            exitCode          = 0
            sessionId         = 'present'
            toolCallSucceeded = $true
            tool              = 'k8s_get_resources'
        }
        $check = Test-DirectMcpEvidenceObject -Evidence $missingError
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 2

        $nonNullError = [pscustomobject]@{
            exitCode          = 0
            sessionId         = 'present'
            toolCallSucceeded = $true
            tool              = 'k8s_get_resources'
            error             = ''
        }
        $check = Test-DirectMcpEvidenceObject -Evidence $nonNullError
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 1
    }

    It 'emits L4/L6 non-claims' {
        $r = Invoke-KagentHealthProfile -Profile DirectMcpServer -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -DirectMcpEvidence $valid
        ($r.doesNotProve -join ' ') | Should Match 'L4'
        ($r.doesNotProve -join ' ') | Should Match 'L6'
        $human = Format-KagentHealthHuman -Result $r
        $human | Should Match 'Direct MCP success does not prove L4 or L6'
    }
}

Describe 'A2ADispatch profile' {
    $pods = @((ConvertFrom-KubectlPodLine -Line 'p1 1/1 Running 0'))
    $agents = @((ConvertFrom-KubectlAgentLine -Line 'a1 Declarative ADK True True'))

    It 'passes accepted/completed task with identifier' {
        $ev = [pscustomobject]@{
            schemaVersion   = '1.0'
            accepted        = $true
            taskState       = 'submitted'
            taskOrMessageId = 'task-fixture-1'
        }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $true
        $r.exitCode | Should Be 0
    }

    It 'fails accepted without taskOrMessageId' {
        $ev = [pscustomobject]@{
            schemaVersion = '1.0'
            accepted      = $true
            taskState     = 'submitted'
        }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 1
        ($r.gates | Where-Object { $_.name -eq 'a2a-dispatch' }).reason | Should Match 'taskOrMessageId'
    }

    It 'passes nested helper JSON contract' {
        $ev = New-ValidA2ADispatchEvidence
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $true
        $r.exitCode | Should Be 0
    }

    It 'rejects wrong schemaVersion' {
        $ev = New-ValidA2ADispatchEvidence
        $ev.schemaVersion = '2.0'
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 2
    }

    It 'rejects inconsistent helper and decision exits' {
        $ev = New-ValidA2ADispatchEvidence
        $ev.helperExit = 1
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 2
        ($r.gates | Where-Object { $_.name -eq 'a2a-dispatch' }).reason | Should Match 'helperExit'
    }

    It 'rejects incomplete nested evidence' {
        $ev = New-ValidA2ADispatchEvidence
        $ev.protocol.PSObject.Properties.Remove('responseIdMatched')
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 2
        ($r.gates | Where-Object { $_.name -eq 'a2a-dispatch' }).reason | Should Match 'responseIdMatched'
    }

    It 'rejects a passing decision with rejected dispatch' {
        $ev = New-ValidA2ADispatchEvidence
        $ev.dispatch.accepted = $false
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 2
    }

    It 'maps a consistent nested gate rejection to exit 1' {
        $ev = New-ValidA2ADispatchEvidence
        $ev.helperExit = 1
        $ev.decision.passed = $false
        $ev.decision.exitCode = 1
        $ev.dispatch.accepted = $false
        $ev.dispatch.taskOrMessageId = $null
        $ev.dispatch.state = $null
        $ev.dispatch.responseKind = $null
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 1
    }

    It 'rejects a gate decision that contradicts accepted dispatch' {
        $ev = New-ValidA2ADispatchEvidence
        $ev.helperExit = 1
        $ev.decision.passed = $false
        $ev.decision.exitCode = 1
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 2
    }

    It 'fails card-only evidence' {
        $ev = [pscustomobject]@{ schemaVersion = '1.0'; cardOnly = $true }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 1
    }

    It 'fails probe-only evidence' {
        $ev = [pscustomobject]@{ schemaVersion = '1.0'; probeOnly = $true }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
    }

    It 'fails -32601' {
        $ev = [pscustomobject]@{
            schemaVersion = '1.0'
            jsonRpcError  = [pscustomobject]@{ code = -32601; message = 'method not found' }
        }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        ($r.gates | Where-Object { $_.name -eq 'a2a-dispatch' }).reason | Should Match '32601'
    }

    It 'fails -32603' {
        $ev = [pscustomobject]@{
            schemaVersion = '1.0'
            jsonRpcError  = [pscustomobject]@{ code = -32603; message = 'internal' }
        }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        ($r.gates | Where-Object { $_.name -eq 'a2a-dispatch' }).reason | Should Match '32603'
    }

    It 'maps transport failure to exit 3' {
        $ev = [pscustomobject]@{ schemaVersion = '1.0'; transportError = 'connection refused' }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.exitCode | Should Be 3
        $r.passed | Should Be $false
    }

    It 'never passes on methodRegistered alone' {
        $ev = [pscustomobject]@{ schemaVersion = '1.0'; methodRegistered = $true }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
    }

    It 'fails missing schemaVersion' {
        $ev = [pscustomobject]@{ accepted = $true; taskOrMessageId = 'task-1'; taskState = 'submitted' }
        $r = Invoke-KagentHealthProfile -Profile A2ADispatch -Pods $pods -Agents $agents -A2ADispatchEvidence $ev
        $r.passed | Should Be $false
        $r.exitCode | Should Be 2
    }
}

Describe 'FullMcpExecution profile' {
    $pods = @((ConvertFrom-KubectlPodLine -Line 'p1 1/1 Running 0'))
    $agents = @((ConvertFrom-KubectlAgentLine -Line 'a1 Declarative ADK True True'))
    $servers = @((ConvertFrom-KubectlRemoteMcpServerLine -Line 'kagent-tool-server STREAMABLE_HTTP http://x True'))
    $direct = [pscustomobject]@{
        exitCode = 0; sessionId = 'present'; toolCallSucceeded = $true
        tool = 'k8s_get_resources'; error = $null
    }
    $a2aOk = [pscustomobject]@{
        schemaVersion   = '1.0'
        accepted        = $true
        taskState       = 'completed'
        taskOrMessageId = 'task-1'
    }
    $evalTime = [datetime]'2026-07-17T12:00:01Z'
    $PSDefaultParameterValues['Invoke-KagentHealthProfile:EvaluationTimeUtc'] = $evalTime
    $PSDefaultParameterValues['Test-AgentMediatedEvidenceObject:EvaluationTimeUtc'] = $evalTime
    $agentOk = [pscustomobject]@{
        schemaVersion  = '1.0'
        evidenceKind   = 'agent-mediated-mcp'
        success        = $true
        observedAt     = '2026-07-17T12:00:00Z'
        target         = [pscustomobject]@{
            clusterContext = 'docker-desktop'
            namespace       = 'kagent'
            agent          = 'k8s-a2a-agent'
            controller     = 'http://127.0.0.1:8083'
            mcpServer      = 'kagent-tool-server'
        }
        a2a            = [pscustomobject]@{
            method           = 'message/stream'
            requestId        = 'req-1'
            taskOrMessageId  = 'task-1'
            acceptedState    = 'completed'
            transport        = [pscustomobject]@{ succeeded = $true; httpStatus = 200 }
            protocol         = [pscustomobject]@{
                jsonRpc = '2.0'; requestId = 'req-1'; responseIdMatched = $true; error = $null
            }
            dispatch         = [pscustomobject]@{
                accepted = $true; taskOrMessageId = 'task-1'; state = 'completed'
            }
        }
        toolInvocation = [pscustomobject]@{
            observed                   = $true
            correlatedTaskOrMessageId  = 'task-1'
            server                     = 'kagent-tool-server'
            tool                       = 'k8s_get_resources'
            argumentsSummary           = [pscustomobject]@{ resourceType = 'pod'; namespace = 'kagent' }
            source                     = [pscustomobject]@{ kind = 'protocol-result'; reference = 'protocol-result:event=2:part=0' }
        }
        result         = [pscustomobject]@{
            returnedThroughA2A         = $true
            toolDerivedResourceNames   = @('k8s-a2a-agent-abc')
            crossCheckResourceNames    = @('k8s-a2a-agent-abc', 'kagent-controller-xyz')
            matched                    = $true
        }
        provenance     = [pscustomobject]@{
            sourceEvidencePath   = 'tests/kagent/fixtures/agent-mediated-source.json'
            freshnessSeconds     = 1
            maxFreshnessSeconds  = 900
            targetBound          = $true
            taskTraceCorrelated  = $true
        }
        decision       = [pscustomobject]@{ passed = $true; exitCode = 0; reason = 'ok' }
    }

    It 'rejects direct MCP evidence alone' {
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -DirectMcpEvidence $direct -A2ADispatchEvidence $a2aOk
        $r.passed | Should Be $false
        ($r.gates | Where-Object { $_.name -eq 'agent-mediated-tool' }).reason | Should Match 'direct MCP'
    }

    It 'rejects RemoteMCPServer acceptance alone' {
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers
        $r.passed | Should Be $false
    }

    It 'rejects A2A without tool evidence' {
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $a2aOk
        $r.passed | Should Be $false
    }

    It 'rejects contradictory separate dispatch evidence' {
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -AgentMediatedEvidence $agentOk `
            -A2ADispatchEvidence ([pscustomobject]@{ schemaVersion = '1.0'; jsonRpcError = [pscustomobject]@{ code = -32601; message = 'method not found' } })
        $r.passed | Should Be $false
    }

    It 'passes complete agent-mediated fixture' {
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $a2aOk -AgentMediatedEvidence $agentOk `
            -EvaluationTimeUtc $evalTime
        $r.passed | Should Be $true
        $r.exitCode | Should Be 0
        ($r.proves -join ' ') | Should Match 'evidence contract'
        ($r.doesNotProve -join ' ') | Should Match 'L6 promotion'
    }

    It 'rejects wrong evidenceKind' {
        $bad = [pscustomobject]@{
            schemaVersion = '1.0'
            evidenceKind  = 'direct-mcp-tool-call'
            observedAt    = ([datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))
        }
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $a2aOk -AgentMediatedEvidence $bad
        $r.passed | Should Be $false
    }

    It 'rejects missing task id' {
        $check = Test-AgentMediatedEvidenceObject -Evidence ([pscustomobject]@{
                schemaVersion  = '1.0'
                evidenceKind   = 'agent-mediated-mcp'
                observedAt     = ([datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))
                target         = $agentOk.target
                a2a            = [pscustomobject]@{
                    method = 'message/stream'; requestId = 'r'; taskOrMessageId = ''; acceptedState = 'completed'
                }
                toolInvocation = $agentOk.toolInvocation
                result         = $agentOk.result
                provenance     = $agentOk.provenance
            })
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 2
    }

    It 'rejects task trace mismatch' {
        $bad = [pscustomobject]@{
            schemaVersion  = '1.0'
            evidenceKind   = 'agent-mediated-mcp'
            success        = $true
            observedAt     = '2026-07-17T12:00:00Z'
            target         = $agentOk.target
            a2a            = $agentOk.a2a
            toolInvocation = [pscustomobject]@{
                observed                  = $true
                correlatedTaskOrMessageId = 'OTHER'
                server                    = 'kagent-tool-server'
                tool                      = 'k8s_get_resources'
                argumentsSummary          = $agentOk.toolInvocation.argumentsSummary
                source                    = $agentOk.toolInvocation.source
            }
            result         = $agentOk.result
            provenance     = $agentOk.provenance
            decision       = $agentOk.decision
        }
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $a2aOk -AgentMediatedEvidence $bad
        $r.passed | Should Be $false
        ($r.gates | Where-Object { $_.name -eq 'agent-mediated-tool' }).reason | Should Match 'mismatch'
    }

    It 'rejects stale evidence' {
        $bad = [pscustomobject]@{
            schemaVersion  = '1.0'
            evidenceKind   = 'agent-mediated-mcp'
            success        = $true
            observedAt     = '2026-07-17T12:00:00Z'
            target         = $agentOk.target
            a2a            = $agentOk.a2a
            toolInvocation = $agentOk.toolInvocation
            result         = $agentOk.result
            provenance     = [pscustomobject]@{
                sourceEvidencePath  = 'tests/kagent/fixtures/agent-mediated-source.json'
                freshnessSeconds    = 901
                maxFreshnessSeconds = 900
                targetBound         = $true
                taskTraceCorrelated = $true
            }
            decision       = $agentOk.decision
        }
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $a2aOk -AgentMediatedEvidence $bad `
            -EvaluationTimeUtc $evalTime.AddSeconds(901)
        $r.passed | Should Be $false
        ($r.gates | Where-Object { $_.name -eq 'agent-mediated-tool' }).reason | Should Match 'stale'
    }

    It 'rejects future-dated evidence' {
        $future = $evalTime.AddMinutes(10).ToString('yyyy-MM-ddTHH:mm:ssZ')
        $bad = [pscustomobject]@{
            schemaVersion  = '1.0'
            evidenceKind   = 'agent-mediated-mcp'
            success        = $true
            observedAt     = $future
            target         = $agentOk.target
            a2a            = $agentOk.a2a
            toolInvocation = $agentOk.toolInvocation
            result         = $agentOk.result
            provenance     = $agentOk.provenance
            decision       = $agentOk.decision
        }
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $a2aOk -AgentMediatedEvidence $bad
        $r.passed | Should Be $false
        ($r.gates | Where-Object { $_.name -eq 'agent-mediated-tool' }).reason | Should Match 'future'
    }

    It 'rejects missing source path' {
        $bad = [pscustomobject]@{
            schemaVersion  = '1.0'
            evidenceKind   = 'agent-mediated-mcp'
            success        = $true
            observedAt     = '2026-07-17T12:00:00Z'
            target         = $agentOk.target
            a2a            = $agentOk.a2a
            toolInvocation = $agentOk.toolInvocation
            result         = $agentOk.result
            provenance     = [pscustomobject]@{
                sourceEvidencePath  = 'tests/kagent/fixtures/does-not-exist.json'
                freshnessSeconds    = 0
                maxFreshnessSeconds = 900
                targetBound         = $true
                taskTraceCorrelated = $true
            }
            decision       = $agentOk.decision
        }
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $a2aOk -AgentMediatedEvidence $bad
        $r.passed | Should Be $false
        $r.exitCode | Should Be 2
    }

    It 'rejects wrong tool' {
        $bad = [pscustomobject]@{
            schemaVersion  = '1.0'
            evidenceKind   = 'agent-mediated-mcp'
            success        = $true
            observedAt     = ([datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))
            target         = $agentOk.target
            a2a            = $agentOk.a2a
            toolInvocation = [pscustomobject]@{
                observed                  = $true
                correlatedTaskOrMessageId = 'task-1'
                server                    = 'kagent-tool-server'
                tool                      = 'wrong_tool'
                argumentsSummary          = $agentOk.toolInvocation.argumentsSummary
                source                    = $agentOk.toolInvocation.source
            }
            result         = $agentOk.result
            provenance     = $agentOk.provenance
            decision       = $agentOk.decision
        }
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $a2aOk -AgentMediatedEvidence $bad
        $r.passed | Should Be $false
    }

    It 'derives A2A acceptance from the same Phase 5E task' {
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -AgentMediatedEvidence $agentOk -EvaluationTimeUtc $evalTime
        $r.passed | Should Be $true
        ($r.gates | Where-Object { $_.name -eq 'a2a-dispatch' }).reason | Should Match 'same-task'
    }

    It 'rejects a separate A2A task mismatch' {
        $other = [pscustomobject]@{
            schemaVersion = '1.0'; accepted = $true; taskState = 'working'; taskOrMessageId = 'task-other'
        }
        $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
            -RemoteMcpServers $servers -A2ADispatchEvidence $other -AgentMediatedEvidence $agentOk `
            -EvaluationTimeUtc $evalTime
        $r.passed | Should Be $false
        $r.exitCode | Should Be 2
        ($r.gates | Where-Object { $_.name -eq 'a2a-dispatch' }).reason | Should Match 'task ID does not match'
    }

    It 'rejects false reported freshness for observedAt' {
        $bad = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $bad.provenance.freshnessSeconds = 0
        $check = Test-AgentMediatedEvidenceObject -Evidence $bad -EvaluationTimeUtc $evalTime.AddSeconds(100)
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 2
        $check.Reason | Should Match 'freshnessSeconds does not match'
    }

    It 'rejects altered maximum freshness' {
        $bad = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $bad.provenance.maxFreshnessSeconds = 901
        $check = Test-AgentMediatedEvidenceObject -Evidence $bad -EvaluationTimeUtc $evalTime
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 2
        $check.Reason | Should Match 'must equal 900'
    }

    It 'rejects missing decision' {
        $bad = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $bad.PSObject.Properties.Remove('decision')
        $check = Test-AgentMediatedEvidenceObject -Evidence $bad -EvaluationTimeUtc $evalTime
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 2
        $check.Reason | Should Match 'missing decision'
    }

    It 'rejects helper and decision exit mismatch' {
        $bad = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $bad | Add-Member -NotePropertyName helperExit -NotePropertyValue 1
        $check = Test-AgentMediatedEvidenceObject -Evidence $bad -EvaluationTimeUtc $evalTime
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 2
        $check.Reason | Should Match 'helperExit'
    }

    It 'rejects incomplete or inconsistent embedded A2A transport protocol dispatch' {
        $missing = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $missing.a2a.PSObject.Properties.Remove('transport')
        (Test-AgentMediatedEvidenceObject -Evidence $missing -EvaluationTimeUtc $evalTime).ExitCodeHint | Should Be 2

        $badProtocol = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $badProtocol.a2a.protocol.responseIdMatched = $false
        (Test-AgentMediatedEvidenceObject -Evidence $badProtocol -EvaluationTimeUtc $evalTime).Reason | Should Match 'protocol'

        $badDispatch = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $badDispatch.a2a.dispatch.taskOrMessageId = 'task-other'
        (Test-AgentMediatedEvidenceObject -Evidence $badDispatch -EvaluationTimeUtc $evalTime).Reason | Should Match 'dispatch'
    }

    It 'rejects wrong controller and tool arguments' {
        $wrongController = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $wrongController.target.controller = 'http://127.0.0.1:9999'
        (Test-AgentMediatedEvidenceObject -Evidence $wrongController -EvaluationTimeUtc $evalTime).Ok | Should Be $false

        $wrongArguments = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $wrongArguments.toolInvocation.argumentsSummary.namespace = 'default'
        $check = Test-AgentMediatedEvidenceObject -Evidence $wrongArguments -EvaluationTimeUtc $evalTime
        $check.Ok | Should Be $false
        $check.Reason | Should Match 'arguments'
    }

    It 'rejects matched true with contradictory result arrays' {
        $bad = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $bad.result.toolDerivedResourceNames = @('missing-pod-xyz')
        $check = Test-AgentMediatedEvidenceObject -Evidence $bad -EvaluationTimeUtc $evalTime
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 2
        $check.Reason | Should Match 'contradicts'
    }

    It 'rejects source traversal and malformed source content' {
        $traversal = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $traversal.provenance.sourceEvidencePath = '../outside.json'
        (Test-AgentMediatedEvidenceObject -Evidence $traversal -EvaluationTimeUtc $evalTime).Reason | Should Match 'escapes repository'

        $malformed = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $malformed.provenance.sourceEvidencePath = 'scripts/kagent/agent_mcp_trace.py'
        (Test-AgentMediatedEvidenceObject -Evidence $malformed -EvaluationTimeUtc $evalTime).Reason | Should Match 'not valid JSON'
    }

    It 'rejects source content mismatch' {
        $bad = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
        $bad.toolInvocation.source.reference = 'protocol-result:event=3:part=0'
        $check = Test-AgentMediatedEvidenceObject -Evidence $bad -EvaluationTimeUtc $evalTime
        $check.Ok | Should Be $false
        $check.ExitCodeHint | Should Be 2
        $check.Reason | Should Match 'source evidence tool marker'
    }

    It 'preserves consistent helper exit classifications 1 2 and 3' {
        foreach ($exit in @(1, 2, 3)) {
            $bad = $agentOk | ConvertTo-Json -Depth 12 | ConvertFrom-Json
            $bad.success = $false
            $bad.decision.passed = $false
            $bad.decision.exitCode = $exit
            $bad | Add-Member -NotePropertyName helperExit -NotePropertyValue $exit
            $r = Invoke-KagentHealthProfile -Profile FullMcpExecution -Pods $pods -Agents $agents `
                -RemoteMcpServers $servers -AgentMediatedEvidence $bad -EvaluationTimeUtc $evalTime
            $r.exitCode | Should Be $exit
            $r.passed | Should Be $false
        }
    }
}

Describe 'Output and exit behavior' {
    It 'JSON output conforms to contract and omits secrets' {
        $pods = @((ConvertFrom-KubectlPodLine -Line 'p1 1/1 Running 0'))
        $agents = @((ConvertFrom-KubectlAgentLine -Line 'a1 Declarative ADK True True'))
        $r = Invoke-KagentHealthProfile -Profile CardLab -Pods $pods -Agents $agents
        $json = ConvertTo-KagentHealthJson -Result $r
        $obj = $json | ConvertFrom-Json
        $obj.schemaVersion | Should Be '1.0'
        $obj.profile | Should Be 'CardLab'
        ($obj.PSObject.Properties.Name -contains 'gates') | Should Be $true
        ($obj.PSObject.Properties.Name -contains 'proves') | Should Be $true
        ($obj.PSObject.Properties.Name -contains 'doesNotProve') | Should Be $true
        $json | Should Not Match 'Authorization'
        $json | Should Not Match 'mcp-session-'
        $json | Should Not Match 'kubeconfig'
    }

    It 'human output has PASS/FAIL labels' {
        $pods = @((ConvertFrom-KubectlPodLine -Line 'p1 1/1 Running 0'))
        $agents = @((ConvertFrom-KubectlAgentLine -Line 'a1 Declarative ADK True True'))
        $r = Invoke-KagentHealthProfile -Profile CardLab -Pods $pods -Agents $agents
        $human = Format-KagentHealthHuman -Result $r
        $human | Should Match '\[PASS\]'
        $human | Should Match 'PROFILE PASSED'
    }

    It 'default profile name CardLab is the documented default' {
        $r = Invoke-KagentHealthProfile -Profile CardLab -Pods @() -Agents @()
        $r.profile | Should Be 'CardLab'
        $r.exitCode | Should Be 1
    }
}
