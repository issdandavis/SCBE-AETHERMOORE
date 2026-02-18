param(
    [string]$SCBEKey = "0123456789abcdef0123456789abcdef",
    [int]$Port = 8001,
    [bool]$KillOnPortInUse = $true,
    [string]$BaseHost = "127.0.0.1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location $repoRoot

if (-not $KillOnPortInUse) {
    $inUse = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '[::]') }
    if ($inUse) {
        Write-Error "Port $Port is already in use. Rerun with -KillOnPortInUse or change -Port."
        exit 1
    }
}

$inUse = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '[::]') }
if ($inUse) {
    $pids = $inUse | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $pids) {
        if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
            Write-Host "Killing PID $processId on port $Port" -ForegroundColor Yellow
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Milliseconds 700
}

$env:SCBE_API_KEY = $SCBEKey
$env:N8N_API_KEY = $SCBEKey
$env:SCBE_BROWSER_WEBHOOK_URL = "http://$BaseHost`:$Port/v1/integrations/n8n/browse"

$args = @(
    "-m", "uvicorn", "agents.browser.main:app",
    "--host", "0.0.0.0",
    "--port", "$Port"
)

$proc = Start-Process -FilePath python -ArgumentList $args -PassThru -WorkingDirectory $repoRoot -WindowStyle Hidden -ErrorAction Stop

try {
    $baseUrl = "http://$BaseHost`:$Port"
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod -Method Get -Uri "$baseUrl/health" -TimeoutSec 3 -ErrorAction Stop
            $ready = $true
            break
        } catch {
            if ($proc.HasExited) {
                throw "Server exited before becoming ready."
            }
        }
    }

    if (-not $ready) {
        throw "Server did not become ready within 20 seconds."
    }

    $headers = @{ "X-API-Key" = $SCBEKey; "Content-Type" = "application/json" }
    $body = @{
        actions = @(
            @{ action = "navigate"; target = "https://example.com"; timeout_ms = 10000 },
            @{ action = "screenshot"; target = "full_page"; timeout_ms = 12000 }
        )
        session_id = "test-session-1"
    } | ConvertTo-Json -Depth 10

    Write-Host "HEALTH:" -ForegroundColor Cyan
    $health | ConvertTo-Json -Depth 5
    Write-Host "BROWSE RESULT:" -ForegroundColor Green
    $result = Invoke-RestMethod -Method Post -Uri "$baseUrl/v1/integrations/n8n/browse" -Headers $headers -Body $body -TimeoutSec 120 -ErrorAction Stop
    $result | ConvertTo-Json -Depth 10

} finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
    }
}
