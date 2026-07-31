[CmdletBinding()]
param(
    [string]$RepoRoot,
    [switch]$RequireEmptyStaging
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}
$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)

function Get-ManifestPaths {
    param([Parameter(Mandatory = $true)][string]$ManifestPath)
    return @(
        Get-Content -LiteralPath $ManifestPath |
            ForEach-Object {
                if ($_ -match "^\s*-\s+path:\s*(.+?)\s*$") {
                    $matches[1].Trim("'`"")
                }
            }
    )
}

function Test-ManifestPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$ManifestPath
    )
    $nativePath = $ManifestPath.Replace("/", [IO.Path]::DirectorySeparatorChar)
    if ($ManifestPath -match "[*?]") {
        return @(Get-ChildItem -Path (Join-Path $Root $nativePath) -ErrorAction SilentlyContinue).Count -gt 0
    }
    return Test-Path -LiteralPath (Join-Path $Root $nativePath)
}

function Test-IsManifestMapped {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string[]]$ManifestPaths
    )
    if ($RelativePath -eq "REPO_MANIFEST.yaml") {
        return $true
    }
    foreach ($mapping in $ManifestPaths) {
        if ($RelativePath -like $mapping) {
            return $true
        }
    }
    return $false
}

function Get-DirtyCanonicalPaths {
    param([Parameter(Mandatory = $true)][string]$Root)
    $sourcePrefixes = @(
        ".agents/",
        ".cursor/",
        ".github/",
        ".project-ai/",
        "config/",
        "deploy/",
        "docs/",
        "evidence/",
        "reports/",
        "scripts/",
        "tests/"
    )
    $sourceFiles = @("AGENTS.md", "constraints.md", "README.md", "pyproject.toml", "uv.lock")
    $paths = [Collections.Generic.List[string]]::new()
    foreach ($line in @(git -C $Root status --porcelain=v1 --untracked-files=all)) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.Length -lt 4) {
            continue
        }
        $path = $line.Substring(3).Trim().Trim('"').Replace("\", "/")
        if ($path -match " -> ") {
            $path = ($path -split " -> ", 2)[1].Trim().Trim('"')
        }
        if (
            $path -in $sourceFiles -or
            @($sourcePrefixes | Where-Object { $path.StartsWith($_, [StringComparison]::OrdinalIgnoreCase) }).Count -gt 0
        ) {
            $paths.Add($path)
        }
    }
    return @($paths | Sort-Object -Unique)
}

function Get-ActiveMarkdownFiles {
    param([Parameter(Mandatory = $true)][string]$Root)
    $files = [Collections.Generic.List[IO.FileInfo]]::new()
    foreach ($file in Get-ChildItem -LiteralPath $Root -File -Filter "*.md" -ErrorAction SilentlyContinue) {
        $files.Add($file)
    }
    foreach ($relativeDirectory in @("docs", "evidence", "reports", ".agents", "scripts/benchmark")) {
        $directory = Join-Path $Root $relativeDirectory
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
            continue
        }
        foreach ($file in Get-ChildItem -LiteralPath $directory -Recurse -File -Filter "*.md" -ErrorAction SilentlyContinue) {
            if (
                $file.FullName -notmatch "[\\/]docs[\\/]archive[\\/]" -and
                $file.FullName -notmatch "[\\/]scripts[\\/]benchmark[\\/]results[\\/]"
            ) {
                $files.Add($file)
            }
        }
    }
    return @($files | Sort-Object FullName -Unique)
}

try {
    $manifestPath = Join-Path $RepoRoot "REPO_MANIFEST.yaml"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "REPO_MANIFEST.yaml is missing."
    }

    $manifestPaths = @(Get-ManifestPaths -ManifestPath $manifestPath)
    $duplicates = @(
        $manifestPaths |
            Group-Object |
            Where-Object Count -GT 1 |
            Select-Object -ExpandProperty Name
    )
    $missingMappings = @(
        $manifestPaths |
            Where-Object { -not (Test-ManifestPath -Root $RepoRoot -ManifestPath $_) }
    )
    $dirtyCanonicalPaths = @(Get-DirtyCanonicalPaths -Root $RepoRoot)
    $unmappedDirtyPaths = @(
        $dirtyCanonicalPaths |
            Where-Object { -not (Test-IsManifestMapped -RelativePath $_ -ManifestPaths $manifestPaths) }
    )

    $brokenLinks = [Collections.Generic.List[string]]::new()
    foreach ($file in Get-ActiveMarkdownFiles -Root $RepoRoot) {
        $content = Get-Content -Raw -LiteralPath $file.FullName
        foreach ($match in [regex]::Matches($content, "!?\[[^\]]*\]\(([^)]+)\)")) {
            $target = $match.Groups[1].Value.Trim()
            if (
                [string]::IsNullOrWhiteSpace($target) -or
                $target.StartsWith("#") -or
                $target -match "^[a-z][a-z0-9+.-]*://" -or
                $target -match "^mailto:"
            ) {
                continue
            }
            $target = $target.Trim("<>")
            $pathOnly = ($target -split "#", 2)[0]
            if ([string]::IsNullOrWhiteSpace($pathOnly)) {
                continue
            }
            $decoded = [Uri]::UnescapeDataString($pathOnly)
            $resolved = [IO.Path]::GetFullPath((Join-Path $file.DirectoryName $decoded))
            if (-not (Test-Path -LiteralPath $resolved)) {
                $relativeFile = [IO.Path]::GetRelativePath($RepoRoot, $file.FullName).Replace("\", "/")
                $brokenLinks.Add("$relativeFile -> $target")
            }
        }
    }

    $stagedPaths = @(
        git -C $RepoRoot diff --cached --name-only |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    $passed = (
        $duplicates.Count -eq 0 -and
        $missingMappings.Count -eq 0 -and
        $unmappedDirtyPaths.Count -eq 0 -and
        $brokenLinks.Count -eq 0 -and
        (-not $RequireEmptyStaging -or $stagedPaths.Count -eq 0)
    )

    [pscustomobject]@{
        schemaVersion = "1.0"
        passed = $passed
        manifest = [pscustomobject]@{
            entries = $manifestPaths.Count
            duplicates = @($duplicates)
            missing = @($missingMappings)
            unmappedDirtyPaths = @($unmappedDirtyPaths)
        }
        links = [pscustomobject]@{
            filesChecked = @(Get-ActiveMarkdownFiles -Root $RepoRoot).Count
            broken = @($brokenLinks)
        }
        staging = [pscustomobject]@{
            requiredEmpty = [bool]$RequireEmptyStaging
            paths = @($stagedPaths)
        }
    } | ConvertTo-Json -Depth 8

    if ($passed) {
        exit 0
    }
    exit 1
} catch {
    [Console]::Error.WriteLine("SLICE_AUDIT_ERROR: $($_.Exception.Message)")
    exit 2
}
