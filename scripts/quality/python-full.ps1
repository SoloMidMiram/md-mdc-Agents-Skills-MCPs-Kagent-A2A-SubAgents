<#
.SYNOPSIS
    Full Python quality check — lint, format, types, tests, coverage, security, audit.
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
Invoke-QualityStep "Mypy" { uv run mypy scripts/kagent }
Invoke-QualityStep "Pytest with coverage" { uv run pytest --cov=scripts/kagent }
Invoke-QualityStep "Coverage report" {
    uv run coverage report --precision=2 --fail-under=80
}
Invoke-QualityStep "Bandit" { uv run bandit -r scripts/kagent -q }
Invoke-QualityStep "Pip-audit" { uv run pip-audit }

Write-Output "=== Python full quality: PASS ==="
