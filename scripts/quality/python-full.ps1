<#
.SYNOPSIS
    Full Python quality check — lint, format, types, tests, coverage, security, audit.
#>
$ErrorActionPreference = "Stop"
Write-Output "=== Ruff check ==="; uv run ruff check .
Write-Output "=== Ruff format ==="; uv run ruff format --check .
Write-Output "=== Mypy ==="; uv run mypy src
Write-Output "=== Pytest with coverage ==="; uv run pytest --cov=src
Write-Output "=== Bandit ==="; uv run bandit -r src -q
Write-Output "=== Pip-audit ==="; uv run pip-audit
Write-Output "=== Python full quality: PASS ==="
