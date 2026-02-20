param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("auth", "check", "dev", "push", "publish")]
    [string]$Mode,

    [Parameter(Mandatory = $false)]
    [string]$Store = "",

    [Parameter(Mandatory = $false)]
    [string]$ThemePath = "",

    [switch]$VerboseOutput
)

$ErrorActionPreference = "Stop"

function Require-Store([string]$modeName, [string]$storeValue) {
    if ([string]::IsNullOrWhiteSpace($storeValue)) {
        throw "Mode '$modeName' requires -Store <your-store>.myshopify.com"
    }
}

if ([string]::IsNullOrWhiteSpace($ThemePath)) {
    $ThemePath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $ThemePath = (Resolve-Path $ThemePath).Path
}

# Force safe home paths to avoid legacy junction scans (e.g., "Application Data").
$env:HOME = $env:USERPROFILE
$env:PNPM_HOME = Join-Path $env:USERPROFILE "AppData\Local\pnpm"
if (-not (Test-Path $env:PNPM_HOME)) {
    New-Item -ItemType Directory -Force -Path $env:PNPM_HOME | Out-Null
}
$env:Path = "$env:PNPM_HOME;$env:Path"

Write-Host "[shopify-safe] ThemePath: $ThemePath"
Write-Host "[shopify-safe] HOME: $($env:HOME)"
Write-Host "[shopify-safe] PNPM_HOME: $($env:PNPM_HOME)"

if ($VerboseOutput) {
    & where.exe pnpm
    & pnpm --version
    & shopify version
}

switch ($Mode) {
    "auth" {
        Push-Location $ThemePath
        try {
            & shopify auth login
        } finally {
            Pop-Location
        }
    }

    "check" {
        & shopify theme check --path $ThemePath
    }

    "dev" {
        Require-Store -modeName $Mode -storeValue $Store
        & shopify theme dev --store $Store --path $ThemePath --open
    }

    "push" {
        Require-Store -modeName $Mode -storeValue $Store
        & shopify theme push --store $Store --path $ThemePath --unpublished
    }

    "publish" {
        Require-Store -modeName $Mode -storeValue $Store
        & shopify theme push --store $Store --path $ThemePath --publish --allow-live
    }
}

