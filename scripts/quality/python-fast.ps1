<#
.SYNOPSIS
    Fast Python quality check — lint, format, and unit tests.
#>
$ErrorActionPreference = "Stop"

function Invoke-QualityStep {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )
    Write-Output "=== $Label ==="
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Quality step failed: $Label (exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

Invoke-QualityStep "Ruff check" { uv run ruff check . }
Invoke-QualityStep "Ruff format" { uv run ruff format --check . }
Invoke-QualityStep "Pytest" { uv run pytest -q }

Write-Output "=== Python fast quality: PASS ==="
