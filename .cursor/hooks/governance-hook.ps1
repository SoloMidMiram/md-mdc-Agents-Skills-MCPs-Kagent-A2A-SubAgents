[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("afterFileEdit", "beforeShellExecution", "stop")]
    [string]$EventName,
    [string]$RepoRoot,
    [string]$LogRoot,
    [Parameter(ValueFromPipeline = $true)]
    [AllowEmptyString()]
    [string]$InputJson
)

begin {
    $chunks = [Collections.Generic.List[string]]::new()
}

process {
    if ($null -ne $InputJson) {
        $chunks.Add($InputJson)
    }
}

end {
    try {
        $modulePath = Join-Path $PSScriptRoot "GovernanceHooks.psm1"
        Import-Module $modulePath -Force -ErrorAction Stop

        if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
            $RepoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
        }
        if ([string]::IsNullOrWhiteSpace($LogRoot)) {
            $LogRoot = Join-Path $RepoRoot "scripts\benchmark\results\hooks"
        }

        $raw = ($chunks -join "`n")
        if ([string]::IsNullOrWhiteSpace($raw)) {
            $raw = [Console]::In.ReadToEnd()
        }
        $inputObject = if ([string]::IsNullOrWhiteSpace($raw)) {
            [pscustomobject]@{}
        } else {
            $raw | ConvertFrom-Json
        }

        $result = Invoke-GovernanceHook `
            -EventName $EventName `
            -InputObject $inputObject `
            -RepoRoot $RepoRoot `
            -LogRoot $LogRoot
        $result.output | ConvertTo-Json -Compress
    } catch {
        # Shadow hooks must never block the agent loop. Do not emit the raw input
        # or exception because either may contain a command, prompt, or path.
        [ordered]@{} | ConvertTo-Json -Compress
    }

    exit 0
}
