param(
    [string]$SCBEKey = "",
    [string]$ListenHost = "0.0.0.0",
    [int]$Port = 8001,
    [switch]$KillOnPortInUse
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

if ([string]::IsNullOrWhiteSpace($SCBEKey)) {
    $SCBEKey = ($env:SCBE_API_KEY | ForEach-Object { $_.Trim() } | Where-Object { $_ })[0]
}
if ([string]::IsNullOrWhiteSpace($SCBEKey)) {
    $SCBEKey = "0123456789abcdef0123456789abcdef"
}

$env:SCBE_API_KEY = $SCBEKey
$env:N8N_API_KEY = $SCBEKey
$env:SCBE_BROWSER_WEBHOOK_URL = "http://127.0.0.1:$Port/v1/integrations/n8n/browse"
if ($KillOnPortInUse) {
    $conns = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '[::]') }
    if ($conns) {
        $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $pids) {
            Write-Host ("Stopping existing process on port {0}: PID {1}" -f $Port, $procId) -ForegroundColor Yellow
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 800
    }
}

$existing = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '[::]') }
if ($existing) {
    Write-Host "Port $Port is still in use. Start with -KillOnPortInUse or use a different -Port value." -ForegroundColor Red
    return
}

Write-Host "======================================" -ForegroundColor Blue
Write-Host "  SCBE AetherBrowse Local Service" -ForegroundColor Blue
Write-Host "======================================" -ForegroundColor Blue
Write-Host "Host:      $ListenHost" -ForegroundColor Cyan
Write-Host "Port:      $Port" -ForegroundColor Cyan
Write-Host "Webhook:   $env:SCBE_BROWSER_WEBHOOK_URL" -ForegroundColor Cyan
Write-Host "Key:       $SCBEKey" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting uvicorn in foreground. Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

python -m uvicorn agents.browser.main:app --host $ListenHost --port $Port
