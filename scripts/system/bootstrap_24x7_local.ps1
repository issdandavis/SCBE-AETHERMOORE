param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [string]$N8nBaseUrl = "http://127.0.0.1:5680",
    [string]$ApiKey = "",
    [string]$ZapierWebhookUrl = "",
    [string]$TelegramConnectorWebhookUrl = "",
    [switch]$RunWatchdogNow = $true,
    [switch]$StartWatchdogLoop = $true,
    [int]$WatchdogIntervalMinutes = 5
)

$ErrorActionPreference = "Stop"

Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:SCBE_MOBILE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:SCBE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = "demo_key_12345"
}

if (-not [string]::IsNullOrWhiteSpace($ZapierWebhookUrl)) {
    $env:ZAPIER_WEBHOOK_URL = $ZapierWebhookUrl
}

if (-not [string]::IsNullOrWhiteSpace($TelegramConnectorWebhookUrl)) {
    $env:TELEGRAM_CONNECTOR_WEBHOOK_URL = $TelegramConnectorWebhookUrl
} elseif (-not $env:TELEGRAM_CONNECTOR_WEBHOOK_URL) {
    $env:TELEGRAM_CONNECTOR_WEBHOOK_URL = "$N8nBaseUrl/webhook/scbe-task"
}

if ($RunWatchdogNow) {
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\system\watchdog_agent_stack_default.ps1"
}

if ($StartWatchdogLoop) {
    $existing = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
        Where-Object { $_.CommandLine -match "run_watchdog_loop\.ps1" } |
        Select-Object -First 1
    if (-not $existing) {
        $wd = Start-Process -FilePath powershell.exe -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "scripts\system\run_watchdog_loop.ps1",
            "-IntervalMinutes", "$WatchdogIntervalMinutes"
        ) -WindowStyle Hidden -PassThru
        Write-Host "[SCBE] Watchdog loop started. PID=$($wd.Id) interval=${WatchdogIntervalMinutes}m"
    } else {
        Write-Host "[SCBE] Watchdog loop already running. PID=$($existing.ProcessId)"
    }
}

powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\system\register_connector_profiles.ps1" `
    -Profile free `
    -BaseUrl $ApiBaseUrl `
    -ApiKey $ApiKey `
    -N8nBaseUrl $N8nBaseUrl `
    -ReplaceExisting

$headers = @{
    "x-api-key" = $ApiKey
}
$connectors = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/mobile/connectors" -Headers $headers
$rows = @($connectors.data | Sort-Object -Property name | ForEach-Object {
    [pscustomobject]@{
        name = $_.name
        id   = $_.connector_id
        url  = $_.endpoint_url
    }
})

Write-Host ""
Write-Host "[SCBE] Active connector map:"
$rows | Format-Table -AutoSize
