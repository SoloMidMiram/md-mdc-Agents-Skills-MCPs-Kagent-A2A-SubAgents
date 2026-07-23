Set-StrictMode -Version Latest

function Get-GovernanceField {
    param(
        [AllowNull()][object]$InputObject,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    if ($null -eq $InputObject) {
        return $null
    }

    $objects = @($InputObject)
    foreach ($containerName in @("tool_input", "toolInput", "input", "arguments")) {
        $container = $InputObject.PSObject.Properties |
            Where-Object Name -IEQ $containerName |
            Select-Object -First 1
        if ($null -ne $container -and $null -ne $container.Value) {
            $objects += $container.Value
        }
    }

    foreach ($object in $objects) {
        foreach ($name in $Names) {
            $property = $object.PSObject.Properties |
                Where-Object Name -IEQ $name |
                Select-Object -First 1
            if ($null -ne $property -and $null -ne $property.Value) {
                return $property.Value
            }
        }
    }

    return $null
}

function Get-GovernanceSessionHash {
    param([AllowNull()][object]$InputObject)

    $sessionId = Get-GovernanceField -InputObject $InputObject -Names @(
        "conversation_id",
        "conversationId",
        "session_id",
        "sessionId"
    )
    if ([string]::IsNullOrWhiteSpace([string]$sessionId)) {
        return "unscoped"
    }

    $bytes = [Text.Encoding]::UTF8.GetBytes([string]$sessionId)
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha256.ComputeHash($bytes)
        return ([Convert]::ToHexString($digest).Substring(0, 16)).ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

function ConvertTo-GovernancePath {
    param(
        [AllowNull()][string]$Path,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return "unknown"
    }

    try {
        $root = [IO.Path]::GetFullPath($RepoRoot).TrimEnd(
            [IO.Path]::DirectorySeparatorChar,
            [IO.Path]::AltDirectorySeparatorChar
        )
        $candidate = if ([IO.Path]::IsPathRooted($Path)) {
            [IO.Path]::GetFullPath($Path)
        } else {
            [IO.Path]::GetFullPath((Join-Path $root $Path))
        }
        $prefix = "$root$([IO.Path]::DirectorySeparatorChar)"
        if (
            -not $candidate.Equals($root, [StringComparison]::OrdinalIgnoreCase) -and
            -not $candidate.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)
        ) {
            return "outside-workspace"
        }

        return [IO.Path]::GetRelativePath($root, $candidate).Replace("\", "/")
    } catch {
        return "invalid-path"
    }
}

function Get-GovernanceRequirements {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    if ($RelativePath -in @("unknown", "outside-workspace", "invalid-path")) {
        return @()
    }

    $requirements = [Collections.Generic.List[string]]::new()
    $normalized = $RelativePath.Replace("\", "/").ToLowerInvariant()
    $extension = [IO.Path]::GetExtension($normalized)

    if ($extension -eq ".py") {
        $requirements.Add("python-tests")
        $requirements.Add("ruff")
    }
    if ($extension -in @(".ps1", ".psm1", ".psd1")) {
        $requirements.Add("powershell-parser")
        if ($normalized -match "(^|/)tests?/") {
            $requirements.Add("pester")
        }
    }
    if ($extension -in @(".md", ".mdc")) {
        $requirements.Add("markdown-links")
    }
    if ($extension -in @(".yaml", ".yml", ".json")) {
        $requirements.Add("structured-data")
    }
    if ($normalized -eq "repo_manifest.yaml" -or $normalized -match "^repo_manifest\.ya?ml$") {
        $requirements.Add("manifest-integrity")
    }
    if (
        $normalized -match "^docs/" -or
        $normalized -match "^evidence/" -or
        $normalized -match "^\.agents/skills/" -or
        $normalized -match "^\.cursor/(rules|hooks)/" -or
        $normalized -eq ".cursor/hooks.json"
    ) {
        $requirements.Add("governance-contract")
    }
    if ($normalized -match "^scripts/benchmark/" -or $normalized -match "^tests/benchmark/") {
        $requirements.Add("governance-benchmark")
        $requirements.Add("governance-contract")
    }
    if ($normalized -match "^(deploy|config/templates)/") {
        $requirements.Add("deployment-validation")
    }

    return @($requirements | Sort-Object -Unique)
}

function Get-GovernanceShellObservation {
    param([AllowNull()][string]$Command)

    $risks = [Collections.Generic.List[string]]::new()
    $validations = [Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrWhiteSpace($Command)) {
        return [pscustomobject]@{
            risks = @()
            validations = @()
        }
    }

    if ($Command -match "(?i)(^|[;&|]\s*)git\s+add\s+(?:-A|--all|\.)(?=\s|$|[;&|])") {
        $risks.Add("broad-staging")
    }
    if (
        $Command -match "(?i)\bgit\s+reset\s+--hard\b" -or
        $Command -match "(?i)\bgit\s+clean\s+-[a-z]*f" -or
        $Command -match "(?i)\bgit\s+(?:checkout|restore)\s+--\s"
    ) {
        $risks.Add("destructive-git")
    }
    if (
        $Command -match "(?i)\bgit\s+push\b" -or
        $Command -match "(?i)\bgh\s+pr\s+(?:create|merge)\b"
    ) {
        $risks.Add("publication")
    }
    if (
        $Command -match "(?i)\bkubectl\s+(?:apply|create|delete|patch|replace|scale)\b" -or
        $Command -match "(?i)\bkubectl\s+rollout\s+restart\b" -or
        $Command -match "(?i)\bhelm\s+(?:install|upgrade|uninstall)\b"
    ) {
        $risks.Add("live-mutation")
    }

    if ($Command -match "(?i)\bpytest\b") {
        $validations.Add("python-tests")
    }
    if ($Command -match "(?i)\bruff(?:\.exe)?\s+check\b") {
        $validations.Add("ruff")
    }
    if ($Command -match "(?i)\bInvoke-Pester\b") {
        $validations.Add("pester")
    }
    if ($Command -match "(?i)(Parser\]::ParseFile|powershell-parser)") {
        $validations.Add("powershell-parser")
    }
    if ($Command -match "(?i)(markdown.*link|link.*audit|broken.*link)") {
        $validations.Add("markdown-links")
    }
    if ($Command -match "(?i)(repo_manifest|manifest.*audit|manifest-integrity)") {
        $validations.Add("manifest-integrity")
    }
    if ($Command -match "(?i)(ConvertFrom-Json|ConvertFrom-Yaml|structured-data)") {
        $validations.Add("structured-data")
    }
    if (
        $Command -match "(?i)AgentGovernanceBenchmark\.Tests\.ps1" -or
        $Command -match "(?i)CursorGovernanceHooks\.Tests\.ps1"
    ) {
        $validations.Add("governance-benchmark")
        $validations.Add("governance-contract")
    }
    if ($Command -match "(?i)(kubeconform|kubectl\s+.*--dry-run|deployment-validation)") {
        $validations.Add("deployment-validation")
    }

    return [pscustomobject]@{
        risks = @($risks | Sort-Object -Unique)
        validations = @($validations | Sort-Object -Unique)
    }
}

function Read-GovernanceState {
    param(
        [Parameter(Mandatory = $true)][string]$StatePath,
        [Parameter(Mandatory = $true)][string]$SessionHash
    )

    if (Test-Path -LiteralPath $StatePath -PathType Leaf) {
        try {
            $state = Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
            if ($state.schemaVersion -eq "1.0" -and $state.sessionHash -eq $SessionHash) {
                return $state
            }
        } catch {
            # Invalid generated state is replaced with a fresh bounded record.
        }
    }

    return [pscustomobject]@{
        schemaVersion = "1.0"
        sessionHash = $SessionHash
        requiredValidations = @()
        observedValidations = @()
        modifiedPaths = @()
        updatedAt = [DateTime]::UtcNow.ToString("o")
    }
}

function Update-GovernanceState {
    param(
        [Parameter(Mandatory = $true)][string]$LogRoot,
        [Parameter(Mandatory = $true)][string]$SessionHash,
        [string[]]$RequiredValidations = @(),
        [string[]]$ObservedValidations = @(),
        [string[]]$ModifiedPaths = @()
    )

    $sessionDirectory = Join-Path $LogRoot "sessions"
    New-Item -ItemType Directory -Path $sessionDirectory -Force | Out-Null
    $statePath = Join-Path $sessionDirectory "$SessionHash.json"
    $state = Read-GovernanceState -StatePath $statePath -SessionHash $SessionHash

    $state.requiredValidations = @(
        @($state.requiredValidations) + @($RequiredValidations) |
            Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
            Sort-Object -Unique
    )
    $state.observedValidations = @(
        @($state.observedValidations) + @($ObservedValidations) |
            Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
            Sort-Object -Unique
    )
    $state.modifiedPaths = @(
        @($state.modifiedPaths) + @($ModifiedPaths) |
            Where-Object { $_ -notin @("unknown", "outside-workspace", "invalid-path") } |
            Sort-Object -Unique |
            Select-Object -First 100
    )
    $state.updatedAt = [DateTime]::UtcNow.ToString("o")

    $state | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $statePath -Encoding utf8
    return $state
}

function Write-GovernanceEvent {
    param(
        [Parameter(Mandatory = $true)][string]$LogRoot,
        [Parameter(Mandatory = $true)][object]$Record
    )

    New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
    $recordPath = Join-Path $LogRoot "events.jsonl"
    $Record | ConvertTo-Json -Depth 8 -Compress |
        Add-Content -LiteralPath $recordPath -Encoding utf8
}

function Invoke-GovernanceHook {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("afterFileEdit", "beforeShellExecution", "stop")]
        [string]$EventName,
        [AllowNull()][object]$InputObject,
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$LogRoot
    )

    $sessionHash = Get-GovernanceSessionHash -InputObject $InputObject
    $requirements = @()
    $observed = @()
    $risks = @()
    $paths = @()
    $relativePath = $null

    switch ($EventName) {
        "afterFileEdit" {
            $path = Get-GovernanceField -InputObject $InputObject -Names @(
                "file_path",
                "filePath",
                "path"
            )
            $relativePath = ConvertTo-GovernancePath -Path ([string]$path) -RepoRoot $RepoRoot
            $requirements = @(Get-GovernanceRequirements -RelativePath $relativePath)
            $paths = @($relativePath)
        }
        "beforeShellExecution" {
            $command = Get-GovernanceField -InputObject $InputObject -Names @(
                "command",
                "shell_command",
                "shellCommand"
            )
            $classification = Get-GovernanceShellObservation -Command ([string]$command)
            $risks = @($classification.risks)
            $observed = @($classification.validations)
        }
    }

    $state = Update-GovernanceState `
        -LogRoot $LogRoot `
        -SessionHash $sessionHash `
        -RequiredValidations $requirements `
        -ObservedValidations $observed `
        -ModifiedPaths $paths
    $missing = @(
        @($state.requiredValidations) |
            Where-Object { $_ -notin @($state.observedValidations) } |
            Sort-Object -Unique
    )

    $record = [ordered]@{
        schemaVersion = "1.0"
        observedAt = [DateTime]::UtcNow.ToString("o")
        mode = "shadow"
        eventName = $EventName
        sessionHash = $sessionHash
        path = $relativePath
        requiredValidations = @($requirements)
        observedValidations = @($observed)
        riskSignals = @($risks)
        missingValidations = if ($EventName -eq "stop") { @($missing) } else { @() }
        blocked = $false
    }
    Write-GovernanceEvent -LogRoot $LogRoot -Record $record

    return [pscustomobject]@{
        output = [ordered]@{}
        record = [pscustomobject]$record
        state = $state
    }
}

Export-ModuleMember -Function @(
    "ConvertTo-GovernancePath",
    "Get-GovernanceRequirements",
    "Get-GovernanceShellObservation",
    "Invoke-GovernanceHook"
)
