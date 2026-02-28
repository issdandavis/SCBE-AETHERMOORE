param(
    [ValidateSet("free", "paid", "all")]
    [string]$Profile = "all",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ApiKey = "",
    [string]$N8nBaseUrl = "",
    [switch]$ReplaceExisting,
    [switch]$DryRun,
    [string]$Output = "artifacts/connector_health/connector_registration_report.json"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "register_connector_profiles.py"
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:SCBE_MOBILE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:SCBE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = "demo_key_12345"
}

if ([string]::IsNullOrWhiteSpace($N8nBaseUrl)) {
    $N8nBaseUrl = $env:N8N_BASE_URL
}

$argsList = @(
    $scriptPath,
    "--profile", $Profile,
    "--base-url", $BaseUrl,
    "--api-key", $ApiKey,
    "--output", $Output
)

if (-not [string]::IsNullOrWhiteSpace($N8nBaseUrl)) {
    $argsList += @("--n8n-base-url", $N8nBaseUrl)
}
if ($ReplaceExisting) { $argsList += "--replace-existing" }
if ($DryRun) { $argsList += "--dry-run" }

python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Connector profile registration failed with exit code $LASTEXITCODE."
}

Write-Host "[SCBE] Connector profile registration complete."
