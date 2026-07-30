# Pester tests for scripts/kubernetes/validate.ps1 and scripts/security/scan.ps1
# Written for Pester 3.x operators (Should Be / Should Match / Should Exist)
# so they run on the repository baseline Pester 3.4.0.

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$pwshExe = (Get-Command pwsh).Source

$validateScript = Join-Path $repoRoot 'scripts\kubernetes\validate.ps1'
$scanScript = Join-Path $repoRoot 'scripts\security\scan.ps1'

function New-TempDir {
    $path = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    return $path
}

function Remove-TempDir {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-ScriptViaChildProcess {
    param(
        [string]$ScriptPath,
        [string[]]$Arguments,
        [string]$PathStub
    )
    $argStr = if ($Arguments -and $Arguments.Count -gt 0 -and [string]::IsNullOrEmpty($Arguments[0]) -eq $false) { " $Arguments" } else { "" }
    $cmd = "`$env:PATH='$PathStub'; & '$ScriptPath'$argStr"
    $output = & $pwshExe -NoProfile -Command $cmd 2>&1
    $ec = $LASTEXITCODE
    # Reset LASTEXITCODE so stale child-process exit codes do not propagate
    # to the outer Pester/CI script that checks $result.FailedCount.
    $global:LASTEXITCODE = 0
    $joined = ($output | Out-String).Trim()
    return @{
        ExitCode = $ec
        Output   = $joined
    }
}

function New-ExitCodeStub {
    param([string]$ToolName, [int]$ExitCode, [string]$TempDir)
    $stubPath = Join-Path $TempDir "$ToolName.ps1"
    $stubContent = "exit $ExitCode"
    Set-Content -LiteralPath $stubPath -Value $stubContent -Encoding ASCII
    return $stubPath
}

Describe 'Kubernetes validation strict mode' {
    It 'fails when kubeconform is missing and -Strict is set' {
        $tempDir = New-TempDir
        try {
            $result = Invoke-ScriptViaChildProcess -ScriptPath $validateScript -Arguments '-Strict' -PathStub $tempDir
            $result.ExitCode | Should Not Be 0
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }

    It 'fails when kube-linter is missing and -Strict is set' {
        $tempDir = New-TempDir
        try {
            # Place a stub kubeconform that exits 0 so only kube-linter is missing
            New-ExitCodeStub -ToolName 'kubeconform' -ExitCode 0 -TempDir $tempDir
            $result = Invoke-ScriptViaChildProcess -ScriptPath $validateScript -Arguments '-Strict' -PathStub $tempDir
            $result.ExitCode | Should Not Be 0
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }

    It 'passes when both tools are present and exit 0' {
        $tempDir = New-TempDir
        try {
            New-ExitCodeStub -ToolName 'kubeconform' -ExitCode 0 -TempDir $tempDir
            New-ExitCodeStub -ToolName 'kube-linter' -ExitCode 0 -TempDir $tempDir
            $result = Invoke-ScriptViaChildProcess -ScriptPath $validateScript -Arguments '-Strict' -PathStub $tempDir
            $result.ExitCode | Should Be 0
            $result.Output | Should Match 'all checks passed'
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }

    It 'propagates nonzero kubeconform exit code' {
        $tempDir = New-TempDir
        try {
            New-ExitCodeStub -ToolName 'kubeconform' -ExitCode 1 -TempDir $tempDir
            New-ExitCodeStub -ToolName 'kube-linter' -ExitCode 0 -TempDir $tempDir
            $result = Invoke-ScriptViaChildProcess -ScriptPath $validateScript -Arguments '-Strict' -PathStub $tempDir
            $result.ExitCode | Should Not Be 0
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }

    It 'propagates nonzero kube-linter exit code' {
        $tempDir = New-TempDir
        try {
            New-ExitCodeStub -ToolName 'kubeconform' -ExitCode 0 -TempDir $tempDir
            New-ExitCodeStub -ToolName 'kube-linter' -ExitCode 1 -TempDir $tempDir
            $result = Invoke-ScriptViaChildProcess -ScriptPath $validateScript -Arguments '-Strict' -PathStub $tempDir
            $result.ExitCode | Should Not Be 0
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }
}

Describe 'Security scan required mode' {
    It 'fails when Trivy is missing and -Required is set' {
        $tempDir = New-TempDir
        try {
            $result = Invoke-ScriptViaChildProcess -ScriptPath $scanScript -Arguments '-Required' -PathStub $tempDir
            $result.ExitCode | Should Not Be 0
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }

    It 'propagates nonzero Trivy exit code' {
        $tempDir = New-TempDir
        try {
            New-ExitCodeStub -ToolName 'trivy' -ExitCode 1 -TempDir $tempDir
            $result = Invoke-ScriptViaChildProcess -ScriptPath $scanScript -Arguments '-Required' -PathStub $tempDir
            $result.ExitCode | Should Not Be 0
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }

    It 'skips when Trivy is missing and -Required is not set' {
        $tempDir = New-TempDir
        try {
            $result = Invoke-ScriptViaChildProcess -ScriptPath $scanScript -Arguments '' -PathStub $tempDir
            $result.ExitCode | Should Be 0
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }
}

Describe 'Kubernetes validation non-strict mode' {
    It 'skips when kubeconform is missing and -Strict is not set' {
        $tempDir = New-TempDir
        try {
            $result = Invoke-ScriptViaChildProcess -ScriptPath $validateScript -Arguments '' -PathStub $tempDir
            $result.ExitCode | Should Be 0
        } finally {
            Remove-TempDir -Path $tempDir
        }
    }
}

# --- kubectl stub helpers for check-kagent-health.ps1 ---

$healthCheckScript = Join-Path $repoRoot 'scripts\kagent\check-kagent-health.ps1'

function New-KubectlStub {
    param([string]$Path)
    $content = @'
param()
$allArgs = $args -join ' '
if ($allArgs -match 'get remotemcpserver') {
    $behavior = [Environment]::GetEnvironmentVariable("KUBECTL_STUB_BEHAVIOR", "Process")
    if ($behavior -eq 'crd-missing') {
        Write-Error "error: the server doesn't have a resource type ""remotemcpserver"""
        exit 1
    } elseif ($behavior -eq 'auth-error') {
        Write-Error "Error from server (Forbidden)"
        exit 1
    }
    exit 0
}
if ($allArgs -match 'get pods') {
    Write-Output "kagent-controller-5d8f7c9b6f-abcde   1/1   Running   0   5m"
    Write-Output "kagent-ui-7f9c8b6a5d-fghij            1/1   Running   0   5m"
    exit 0
}
if ($allArgs -match 'get agent') {
    Write-Output "k8s-a2a-agent   A2A   v1   True   True"
    exit 0
}
exit 0
'@
    Set-Content -LiteralPath $Path -Value $content -Encoding ASCII
}

function Invoke-HealthCheckViaChildProcess {
    param(
        [string]$KubectlBehavior = 'present',
        [string]$Profile = 'CardLab',
        [string]$ExtraArgs = ''
    )
    $tempDir = New-TempDir
    try {
        New-KubectlStub -Path (Join-Path $tempDir 'kubectl.ps1')
        # Write a wrapper script to avoid -Command exit-code issues with [Console]::Error
        $wrapper = Join-Path $tempDir 'runner.ps1'
        $wrapperContent = @"
`$env:PATH='$tempDir'
`$env:KUBECTL_STUB_BEHAVIOR='$KubectlBehavior'
& '$healthCheckScript' -Profile $Profile $ExtraArgs
exit `$LASTEXITCODE
"@
        Set-Content -LiteralPath $wrapper -Value $wrapperContent -Encoding ASCII
        $output = & $pwshExe -NoProfile -File $wrapper 2>&1
        $ec = $LASTEXITCODE
        # Reset LASTEXITCODE so stale child-process exit codes do not propagate
        # to the outer Pester/CI script that checks $result.FailedCount.
        $global:LASTEXITCODE = 0
        $joined = ($output | Out-String).Trim()
        return @{
            ExitCode = $ec
            Output   = $joined
        }
    } finally {
        Remove-TempDir -Path $tempDir
    }
}

Describe 'Check-kagent-health CRD behavior' {
    It 'CardLab + missing CRD + healthy pods/agents exits 0' {
        $result = Invoke-HealthCheckViaChildProcess -KubectlBehavior 'crd-missing' -Profile 'CardLab'
        $result.ExitCode | Should Be 0
        $result.Output | Should Match 'CRD not found'
    }

    It 'CardLab + auth error exits 3' {
        $result = Invoke-HealthCheckViaChildProcess -KubectlBehavior 'auth-error' -Profile 'CardLab'
        $result.ExitCode | Should Not Be 0
        $result.Output | Should Match 'FAIL'
    }

    It 'DirectMcpServer + missing CRD exits 3 with CRD-required message' {
        $dummyPath = Join-Path $env:TEMP "kagent_test_direct_$([System.Guid]::NewGuid().ToString()).json"
        try {
            Set-Content -LiteralPath $dummyPath -Value '{}' -Encoding ASCII
            $result = Invoke-HealthCheckViaChildProcess -KubectlBehavior 'crd-missing' -Profile 'DirectMcpServer' -ExtraArgs "-DirectMcpResultPath '$dummyPath'"
            $result.ExitCode | Should Be 3
            $result.Output | Should Match 'RemoteMCPServer CRD is required'
        } finally {
            Remove-Item -LiteralPath $dummyPath -Force -ErrorAction SilentlyContinue
        }
    }

    It 'A2ADispatch + missing CRD exits 3 with CRD-required message' {
        $result = Invoke-HealthCheckViaChildProcess -KubectlBehavior 'crd-missing' -Profile 'A2ADispatch'
        $result.ExitCode | Should Be 3
        $result.Output | Should Match 'RemoteMCPServer CRD is required'
    }

    It 'FullMcpExecution + missing CRD exits 3 with CRD-required message' {
        $result = Invoke-HealthCheckViaChildProcess -KubectlBehavior 'crd-missing' -Profile 'FullMcpExecution'
        $result.ExitCode | Should Be 3
        $result.Output | Should Match 'RemoteMCPServer CRD is required'
    }
}
