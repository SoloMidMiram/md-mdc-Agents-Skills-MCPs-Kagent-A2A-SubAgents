<#
.SYNOPSIS
    Fast Python quality check — lint, format, and unit tests.
#>
$ErrorActionPreference = "Stop"
Write-Output "=== Ruff check ==="; uv run ruff check .
Write-Output "=== Ruff format ==="; uv run ruff format --check .
Write-Output "=== Pytest ==="; uv run pytest -q
Write-Output "=== Python fast quality: PASS ==="
