<#
.SYNOPSIS
    Bootstrap the repo's Python workspace and VS Code Python extension bundle.

.DESCRIPTION
    Installs the standard Python/Ruff VS Code extensions for the current user
    and runs uv sync so the repository virtual environment is ready.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$SkipExtensions,
    [switch]$SkipSync
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExtensions = @(
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "ms-python.debugpy",
    "ms-python.mypy-type-checker"
)

function Get-InstalledExtensions {
    if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
        throw "VS Code command line 'code' was not found in PATH."
    }

    $listed = & code --list-extensions 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to enumerate VS Code extensions with 'code --list-extensions'."
    }

    return $listed
}

if (-not $SkipExtensions) {
    $installedExtensions = Get-InstalledExtensions

    foreach ($extension in $pythonExtensions) {
        if ($installedExtensions -contains $extension) {
            Write-Output "Extension already installed: $extension"
            continue
        }

        if ($PSCmdlet.ShouldProcess("VS Code extension $extension", "install")) {
            & code --install-extension $extension --force
        }
    }
}

if (-not $SkipSync) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv was not found in PATH. Install uv first, then rerun this script."
    }

    if ($PSCmdlet.ShouldProcess("Repository environment", "uv sync")) {
        & uv sync
    }
}

Write-Output "=== Python workspace bootstrap complete ==="
