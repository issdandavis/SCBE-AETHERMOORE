<#
.SYNOPSIS
    Kerrigan — One-click launcher for the AI Home.
    Starts AetherCode gateway (port 8500), then opens the dashboard.

.DESCRIPTION
    Port map:
      8001 — SCBE Bridge
      8002 — Webhook server
      8200 — PollyPad IDE
      8300 — AetherNet Social
      8400 — Playwright (untouched)
      8500 — AetherCode (this product)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\start_kerrigan.ps1
    powershell -ExecutionPolicy Bypass -File scripts\start_kerrigan.ps1 -RuntimeOnly
#>

param(
    [switch]$RuntimeOnly,
    [switch]$NoBrowser,
    [int]$Port = 8500
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$RepoRoot\src\aethercode")) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

Write-Host ""
Write-Host "  KERRIGAN — AI Home" -ForegroundColor Cyan
Write-Host "  ==================" -ForegroundColor DarkCyan
Write-Host "  AetherCode gateway on port $Port" -ForegroundColor DarkGray
Write-Host ""

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  [ERROR] Python not found. Install Python 3.11+." -ForegroundColor Red
    exit 1
}

# Check FastAPI
$hasFastAPI = python -c "import fastapi; print('ok')" 2>$null
if ($hasFastAPI -ne "ok") {
    Write-Host "  [WARN] FastAPI not installed. Installing..." -ForegroundColor Yellow
    pip install fastapi uvicorn websockets pydantic --quiet
}

# Start AetherCode gateway
Write-Host "  [1/2] Starting AetherCode on port $Port..." -ForegroundColor Green

$runtimeJob = Start-Job -ScriptBlock {
    param($root, $port)
    Set-Location $root
    python -m uvicorn src.aethercode.gateway:app --host 127.0.0.1 --port $port --log-level info
} -ArgumentList $RepoRoot, $Port

# Wait for ready
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
}

if ($ready) {
    Write-Host "  [OK] AetherCode live at http://127.0.0.1:$Port" -ForegroundColor Green
} else {
    Write-Host "  [WARN] AetherCode may still be starting..." -ForegroundColor Yellow
}

if ($RuntimeOnly -or $NoBrowser) {
    Write-Host ""
    Write-Host "  App:       http://127.0.0.1:$Port/" -ForegroundColor Cyan
    Write-Host "  Dashboard: http://127.0.0.1:$Port/home" -ForegroundColor Cyan
    Write-Host "  API Docs:  http://127.0.0.1:$Port/docs" -ForegroundColor Cyan
    Write-Host "  Status:    http://127.0.0.1:$Port/api/status" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
    Wait-Job $runtimeJob
} else {
    Write-Host "  [2/2] Opening dashboard in browser..." -ForegroundColor Green
    Start-Process "http://127.0.0.1:$Port/home"

    Write-Host ""
    Write-Host "  AetherCode running. Press Ctrl+C to stop." -ForegroundColor DarkGray
    Wait-Job $runtimeJob
}

Stop-Job $runtimeJob -ErrorAction SilentlyContinue
Remove-Job $runtimeJob -ErrorAction SilentlyContinue
