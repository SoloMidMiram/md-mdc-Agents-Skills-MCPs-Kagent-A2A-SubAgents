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
