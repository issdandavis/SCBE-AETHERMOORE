param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('store', 'resolve', 'list', 'doctor')]
    [string]$Action,

    [string]$Service,

    [string]$EnvName
)

$ErrorActionPreference = 'Stop'

$mirror = 'C:\Users\issda\.codex\skills\scbe-api-key-local-mirror\scripts\key_mirror.py'

if (-not (Test-Path $mirror)) {
    throw "key_mirror.py not found at $mirror"
}

function Get-DefaultEnvName([string]$serviceName) {
    if ([string]::IsNullOrWhiteSpace($serviceName)) {
        return $null
    }
    $normalized = ($serviceName -replace '[^A-Za-z0-9]', '_').ToUpperInvariant()
    return "${normalized}_API_KEY"
}

switch ($Action) {
    'doctor' {
        python $mirror doctor
        break
    }
    'list' {
        python $mirror list
        break
    }
    'store' {
        if ([string]::IsNullOrWhiteSpace($Service)) {
            throw "Service is required for store."
        }
        if ([string]::IsNullOrWhiteSpace($EnvName)) {
            $EnvName = Get-DefaultEnvName $Service
        }
        $value = Read-Host "Enter key for $Service" -MaskInput
        if ([string]::IsNullOrWhiteSpace($value)) {
            throw "No key entered."
        }
        Set-Item -Path "Env:$EnvName" -Value $value
        try {
            python $mirror store --service $Service --env $EnvName
        }
        finally {
            Remove-Item "Env:$EnvName" -ErrorAction SilentlyContinue
        }
        break
    }
    'resolve' {
        if ([string]::IsNullOrWhiteSpace($Service)) {
            throw "Service is required for resolve."
        }
        if ([string]::IsNullOrWhiteSpace($EnvName)) {
            $EnvName = Get-DefaultEnvName $Service
        }
        python $mirror resolve --service $Service --env-out $EnvName
        Write-Output "Resolved $Service into process env var $EnvName"
        break
    }
}
