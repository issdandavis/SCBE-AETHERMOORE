[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Store,

    [string]$ThemePath = "shopify/aethermoore-creator-os",
    [string]$ThemeName = "Aethermoore Creator OS",
    [switch]$Publish,
    [switch]$SkipThemeCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Test-PlaceholderStore {
    param([Parameter(Mandatory = $true)][string]$Value)
    $normalized = $Value.Trim().ToLowerInvariant()
    if ($normalized -match "^https?://") {
        try {
            $uri = [uri]$normalized
            $normalized = $uri.Host.ToLowerInvariant()
        }
        catch {
            # Keep the raw normalized value for validation fallback.
        }
    }
    return ($normalized -match "^(your-store|example|test-store|<store>|store)\.myshopify\.com$") -or
           ($normalized -eq "your-store") -or
           ($normalized -eq "example")
}

function Invoke-ShopifyCommand {
    param(
        [Parameter(Mandatory = $true)][string[]]$Args,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$LogPath
    )
    $cmdText = "shopify $($Args -join ' ')"
    Write-Host ">> $cmdText"
    Add-Content -Path $LogPath -Value "### $Label`n$cmdText"

    $raw = (& shopify @Args 2>&1 | Out-String).Trim()
    Add-Content -Path $LogPath -Value "$raw`n"
    if ($LASTEXITCODE -ne 0) {
        if ($raw -match 'Invalid API key or access token|status":401|GraphQL Error \(Code: 401\)') {
            throw @"
Shopify command failed ($Label) with auth error (401).
Likely causes:
- wrong store domain
- expired Shopify CLI session
- store not accessible by current account

Run these:
  shopify auth logout
  shopify auth login
  shopify theme list --store $Store --json

Then rerun:
  pwsh -File scripts/shopify_storefront_bootstrap.ps1 -Store $Store $(if($Publish){'-Publish'})

Details: $LogPath
"@
        }
        throw "Shopify command failed ($Label). See $LogPath"
    }
    return $raw
}

Require-Command -Name "shopify"

if (Test-PlaceholderStore -Value $Store) {
    throw "Store looks like a placeholder (`$Store`). Use your real store domain (example: mystore.myshopify.com)."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$resolvedThemePath = (Resolve-Path (Join-Path $repoRoot $ThemePath)).Path

$artifactDir = Join-Path $repoRoot "artifacts/shopify-bootstrap"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $artifactDir "$stamp-bootstrap.log"
$summaryPath = Join-Path $artifactDir "$stamp-summary.json"

Write-Host "[shopify-bootstrap] store=$Store"
Write-Host "[shopify-bootstrap] theme_path=$resolvedThemePath"
Write-Host "[shopify-bootstrap] publish=$($Publish.IsPresent)"
Write-Host "[shopify-bootstrap] log=$logPath"

Invoke-ShopifyCommand -Args @("theme", "list", "--store", $Store, "--json") -Label "store_preflight" -LogPath $logPath | Out-Null

if (-not $SkipThemeCheck) {
    Invoke-ShopifyCommand -Args @("theme", "check", "--path", $resolvedThemePath) -Label "theme_check" -LogPath $logPath | Out-Null
}

$pushArgs = @("theme", "push", "--json", "--store", $Store, "--path", $resolvedThemePath)
if ($Publish) {
    $pushArgs += "--publish"
}
else {
    $pushArgs += "--unpublished"
}
if ($ThemeName) {
    $pushArgs += @("--theme", $ThemeName)
}

$pushOutput = Invoke-ShopifyCommand -Args $pushArgs -Label "theme_push" -LogPath $logPath

$jsonMatch = [regex]::Match($pushOutput, "\{[\s\S]*\}$")
$theme = $null
if ($jsonMatch.Success) {
    try {
        $payload = $jsonMatch.Value | ConvertFrom-Json
        $theme = $payload.theme
    }
    catch {
        Write-Warning "Could not parse JSON response from theme push."
    }
}
else {
    Write-Warning "No JSON payload found in theme push output."
}

$summary = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    store = $Store
    theme_path = $resolvedThemePath
    publish_requested = [bool]$Publish.IsPresent
    log_path = $logPath
}

if ($null -ne $theme) {
    $summary.theme_id = $theme.id
    $summary.theme_name = $theme.name
    $summary.theme_role = $theme.role
    $summary.editor_url = $theme.editor_url
    $summary.preview_url = $theme.preview_url
}

($summary | ConvertTo-Json -Depth 5) | Set-Content -Path $summaryPath -Encoding UTF8

Write-Host "[shopify-bootstrap] summary=$summaryPath"
if ($summary.Contains("preview_url")) {
    Write-Host "[shopify-bootstrap] preview=$($summary.preview_url)"
}
if ($summary.Contains("editor_url")) {
    Write-Host "[shopify-bootstrap] editor=$($summary.editor_url)"
}
