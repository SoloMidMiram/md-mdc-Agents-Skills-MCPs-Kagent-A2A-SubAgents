# Pester tests for scripts/kubernetes/validate.ps1 and scripts/security/scan.ps1
# Written for Pester 3.x operators (Should Be / Should Match / Should Exist)
# so they run on the repository baseline Pester 3.4.0.

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')

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
            $oldPath = $env:PATH
            $env:PATH = $tempDir
            $scriptBlock = {
                param($Script)
                & $Script -Strict
            }
            & $scriptBlock -Script $validateScript 2>&1 | Out-Null
            $exitCode = $LASTEXITCODE
            $env:PATH = $oldPath
            $exitCode | Should Not Be 0
        } finally {
            $env:PATH = $oldPath
            Remove-TempDir -Path $tempDir
        }
    }

    It 'fails when kube-linter is missing and -Strict is set' {
        $tempDir = New-TempDir
        try {
            $oldPath = $env:PATH
            $env:PATH = $tempDir
            # Place a stub kubeconform that exits 0 so only kube-linter is missing
            New-ExitCodeStub -ToolName 'kubeconform.cmd' -ExitCode 0 -TempDir $tempDir
            # On Windows, PowerShell resolves .ps1, .cmd, .exe; place a cmd stub
            $stubKubeconform = Join-Path $tempDir 'kubeconform.cmd'
            Set-Content -LiteralPath $stubKubeconform -Value '@exit /b 0' -Encoding ASCII
            $scriptBlock = {
                param($Script)
                & $Script -Strict
            }
            & $scriptBlock -Script $validateScript 2>&1 | Out-Null
            $exitCode = $LASTEXITCODE
            $env:PATH = $oldPath
            $exitCode | Should Not Be 0
        } finally {
            $env:PATH = $oldPath
            Remove-TempDir -Path $tempDir
        }
    }

    It 'passes when both tools are present and exit 0' {
        $tempDir = New-TempDir
        try {
            $oldPath = $env:PATH
            # Place stub .cmd wrappers for both tools
            $stubConform = Join-Path $tempDir 'kubeconform.cmd'
            Set-Content -LiteralPath $stubConform -Value '@exit /b 0' -Encoding ASCII
            $stubLinter = Join-Path $tempDir 'kube-linter.cmd'
            Set-Content -LiteralPath $stubLinter -Value '@exit /b 0' -Encoding ASCII
            $env:PATH = $tempDir
            $output = & $validateScript -Strict 2>&1
            $exitCode = $LASTEXITCODE
            $env:PATH = $oldPath
            $exitCode | Should Be 0
            $output | Should Match 'all checks passed'
        } finally {
            $env:PATH = $oldPath
            Remove-TempDir -Path $tempDir
        }
    }

    It 'propagates nonzero kubeconform exit code' {
        $tempDir = New-TempDir
        try {
            $oldPath = $env:PATH
            # Stub kubeconform exits 1, kube-linter exits 0
            $stubConform = Join-Path $tempDir 'kubeconform.cmd'
            Set-Content -LiteralPath $stubConform -Value '@exit /b 1' -Encoding ASCII
            $stubLinter = Join-Path $tempDir 'kube-linter.cmd'
            Set-Content -LiteralPath $stubLinter -Value '@exit /b 0' -Encoding ASCII
            $env:PATH = $tempDir
            & $validateScript -Strict 2>&1 | Out-Null
            $exitCode = $LASTEXITCODE
            $env:PATH = $oldPath
            $exitCode | Should Not Be 0
        } finally {
            $env:PATH = $oldPath
            Remove-TempDir -Path $tempDir
        }
    }
}

Describe 'Security scan required mode' {
    It 'fails when Trivy is missing and -Required is set' {
        $tempDir = New-TempDir
        try {
            $oldPath = $env:PATH
            $env:PATH = $tempDir
            & $scanScript -Required 2>&1 | Out-Null
            $exitCode = $LASTEXITCODE
            $env:PATH = $oldPath
            $exitCode | Should Not Be 0
        } finally {
            $env:PATH = $oldPath
            Remove-TempDir -Path $tempDir
        }
    }

    It 'propagates nonzero Trivy exit code' {
        $tempDir = New-TempDir
        try {
            $oldPath = $env:PATH
            # Stub trivy exits 1
            $stubTrivy = Join-Path $tempDir 'trivy.cmd'
            Set-Content -LiteralPath $stubTrivy -Value '@exit /b 1' -Encoding ASCII
            $env:PATH = $tempDir
            & $scanScript -Required 2>&1 | Out-Null
            $exitCode = $LASTEXITCODE
            $env:PATH = $oldPath
            $exitCode | Should Not Be 0
        } finally {
            $env:PATH = $oldPath
            Remove-TempDir -Path $tempDir
        }
    }

    It 'skips when Trivy is missing and -Required is not set' {
        $tempDir = New-TempDir
        try {
            $oldPath = $env:PATH
            $env:PATH = $tempDir
            & $scanScript 2>&1 | Out-Null
            $exitCode = $LASTEXITCODE
            $env:PATH = $oldPath
            $exitCode | Should Be 0
        } finally {
            $env:PATH = $oldPath
            Remove-TempDir -Path $tempDir
        }
    }
}

Describe 'Kubernetes validation non-strict mode' {
    It 'skips when kubeconform is missing and -Strict is not set' {
        $tempDir = New-TempDir
        try {
            $oldPath = $env:PATH
            $env:PATH = $tempDir
            & $validateScript 2>&1 | Out-Null
            $exitCode = $LASTEXITCODE
            $env:PATH = $oldPath
            $exitCode | Should Be 0
        } finally {
            $env:PATH = $oldPath
            Remove-TempDir -Path $tempDir
        }
    }
}
