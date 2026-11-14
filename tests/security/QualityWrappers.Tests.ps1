# The wrappers must stop at the first failed native command and never print PASS.
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '../..')
$pwsh = (Get-Command pwsh).Source

Describe 'Fail-closed quality wrappers' {
    foreach ($wrapper in @('python-fast.ps1', 'python-full.ps1')) {
        It "$wrapper stops after a native failure" {
            $stub = Join-Path $TestDrive ($wrapper.Replace('.ps1', '') + '-fail')
            New-Item -ItemType Directory -Path $stub -Force | Out-Null
            $calls = Join-Path $stub 'calls.txt'
            $body = "`$args -join ' ' | Add-Content -LiteralPath '$calls'; exit 7"
            Set-Content -LiteralPath (Join-Path $stub 'uv.ps1') -Value $body
            $script = Join-Path $repoRoot "scripts/quality/$wrapper"
            $command = "`$env:PATH='$stub;' + `$env:PATH; & '$script'"
            $output = & $pwsh -NoProfile -Command $command 2>&1 | Out-String
            $LASTEXITCODE | Should Not Be 0
            $output | Should Not Match 'quality: PASS'
            @(Get-Content -LiteralPath $calls).Count | Should Be 1
            $global:LASTEXITCODE = 0
        }
    }
    It 'fast wrapper reports success only after all three commands pass' {
        $stub = Join-Path $TestDrive 'uv-pass'
        New-Item -ItemType Directory -Path $stub -Force | Out-Null
        $calls = Join-Path $stub 'calls.txt'
        Set-Content -LiteralPath (Join-Path $stub 'uv.ps1') -Value "`$args -join ' ' | Add-Content -LiteralPath '$calls'; exit 0"
        $script = Join-Path $repoRoot 'scripts/quality/python-fast.ps1'
        $output = & $pwsh -NoProfile -Command "`$env:PATH='$stub;' + `$env:PATH; & '$script'" 2>&1 | Out-String
        $LASTEXITCODE | Should Be 0
        $output | Should Match 'fast quality: PASS'
        @(Get-Content -LiteralPath $calls).Count | Should Be 3
    }
}
