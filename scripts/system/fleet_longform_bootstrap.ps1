param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$BridgeUrl = "http://127.0.0.1:8002",
    [string]$BrowserUrl = "http://127.0.0.1:8012",
    [string]$N8nUrl = "http://127.0.0.1:5680",
    [string]$MobileApiKey = "",
    [string]$BridgeApiKey = "",
    [switch]$SkipOAuthTemplate,
    [switch]$SkipSmoke,
    [switch]$SkipConnectorRegistration,
    [switch]$SkipPaid,
    [switch]$ReplaceExistingConnectors,
    [switch]$FullConnectorHealth
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($MobileApiKey)) {
    $MobileApiKey = $env:SCBE_MOBILE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($MobileApiKey)) {
    $MobileApiKey = "demo_key_12345"
}

if ([string]::IsNullOrWhiteSpace($BridgeApiKey)) {
    $BridgeApiKey = $env:SCBE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($BridgeApiKey)) {
    $BridgeApiKey = $env:N8N_API_KEY
}
if ([string]::IsNullOrWhiteSpace($BridgeApiKey)) {
    $BridgeApiKey = $env:SCBE_BROWSER_API_KEY
}
if ([string]::IsNullOrWhiteSpace($BridgeApiKey)) {
    $BridgeApiKey = "test-key"
}

Write-Host "[SCBE] Fleet long-form bootstrap starting..."
Write-Host "  API: $ApiBaseUrl"
Write-Host "  Bridge: $BridgeUrl"
Write-Host "  Browser: $BrowserUrl"
Write-Host "  n8n: $N8nUrl"

if (-not $SkipOAuthTemplate) {
    Write-Host ""
    Write-Host "[SCBE] Step 1/4: OAuth template refresh"
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\system\quick_oauth_bootstrap.ps1 -Profile all -IncludeCurrentSession -OutputPath artifacts\connector_health\.env.all.oauth.sample
}

if (-not $SkipSmoke) {
    Write-Host ""
    Write-Host "[SCBE] Step 2/4: Stack smoke validation"
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\system\smoke_n8n_bridge.ps1 `
        -BridgeUrl $BridgeUrl `
        -BrowserUrl $BrowserUrl `
        -N8nUrl $N8nUrl `
        -StartupWaitSec 15 `
        -ProbeWebhook `
        -Output artifacts\system_smoke\fleet_bootstrap_smoke.json
}

if (-not $SkipConnectorRegistration) {
    Write-Host ""
    Write-Host "[SCBE] Step 3/4: Register free connectors"
    $freeArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", "scripts\system\register_connector_profiles.ps1",
        "-Profile", "free",
        "-BaseUrl", $ApiBaseUrl,
        "-N8nBaseUrl", $N8nUrl,
        "-ApiKey", $MobileApiKey,
        "-Output", "artifacts\connector_health\connector_registration_free.json"
    )
    if ($ReplaceExistingConnectors) { $freeArgs += "-ReplaceExisting" }
    powershell @freeArgs

    if (-not $SkipPaid) {
        Write-Host ""
        Write-Host "[SCBE] Step 3b/4: Register paid connectors"
        $paidArgs = @(
            "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", "scripts\system\register_connector_profiles.ps1",
            "-Profile", "paid",
            "-BaseUrl", $ApiBaseUrl,
            "-N8nBaseUrl", $N8nUrl,
            "-ApiKey", $MobileApiKey,
            "-Output", "artifacts\connector_health\connector_registration_paid.json"
        )
        if ($ReplaceExistingConnectors) { $paidArgs += "-ReplaceExisting" }
        powershell @paidArgs
    }
}

Write-Host ""
Write-Host "[SCBE] Step 4/4: Connector matrix health"
$checks = "n8n bridge playwright"
if ($FullConnectorHealth) {
    $checks = "github notion drive huggingface airtable zapier telegram n8n bridge playwright"
}

python scripts\connector_health_check.py `
    --checks $checks.Split(" ") `
    --n8n-base-url $N8nUrl `
    --bridge-base-url $BridgeUrl `
    --playwright-base-url $BrowserUrl `
    --bridge-api-key $BridgeApiKey `
    --output artifacts\connector_health\fleet_bootstrap_connector_health.json

if ($LASTEXITCODE -ne 0) {
    throw "Connector matrix health reported actionable failures."
}

Write-Host ""
Write-Host "[SCBE] Fleet long-form bootstrap completed."
