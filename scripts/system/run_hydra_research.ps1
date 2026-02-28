# run_hydra_research.ps1 — Orchestration entrypoint for HYDRA Research Stack
# Starts all required services and verifies health before enabling research
param(
    [switch]$StartBridge,
    [switch]$StartOpenClaw,
    [switch]$StartN8n,
    [switch]$HealthOnly,
    [switch]$All
)

$ErrorActionPreference = "Stop"
$ScbeRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "=== HYDRA Research Stack Orchestrator ===" -ForegroundColor Cyan
Write-Host "SCBE Root: $ScbeRoot"
Write-Host ""

# Health check function
function Test-ServiceHealth {
    param([string]$Name, [string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing
        Write-Host "  [UP] $Name" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  [DOWN] $Name" -ForegroundColor Red
        return $false
    }
}

# Run health checks
Write-Host "--- Service Health ---" -ForegroundColor Yellow
$bridgeUp = Test-ServiceHealth -Name "SCBE Bridge (8001)" -Url "http://127.0.0.1:8001/health"
$openclawUp = Test-ServiceHealth -Name "OpenClaw GW (18789)" -Url "http://127.0.0.1:18789/health"
$n8nUp = Test-ServiceHealth -Name "n8n (5678)" -Url "http://127.0.0.1:5678/healthz"

# Playwright check
try {
    python -c "import playwright" 2>$null
    Write-Host "  [OK] Playwright available" -ForegroundColor Green
    $pwUp = $true
} catch {
    Write-Host "  [MISSING] Playwright — run: pip install playwright && playwright install" -ForegroundColor Red
    $pwUp = $false
}

Write-Host ""

if ($HealthOnly) {
    exit 0
}

# Start services if requested
if ($All -or $StartBridge) {
    if (-not $bridgeUp) {
        Write-Host "Starting SCBE Bridge..." -ForegroundColor Cyan
        Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m uvicorn workflows.n8n.scbe_n8n_bridge:app --host 127.0.0.1 --port 8001" -WorkingDirectory $ScbeRoot
        Start-Sleep -Seconds 3
    }
}

if ($All -or $StartOpenClaw) {
    if (-not $openclawUp) {
        $composeFile = Join-Path $ScbeRoot "external\openclaw\docker-compose.yml"
        if (Test-Path $composeFile) {
            Write-Host "Starting OpenClaw Gateway via Docker..." -ForegroundColor Cyan
            docker compose -f $composeFile up -d
        } else {
            Write-Host "OpenClaw docker-compose.yml not found at $composeFile" -ForegroundColor Red
        }
    }
}

if ($All -or $StartN8n) {
    if (-not $n8nUp) {
        Write-Host "Starting n8n..." -ForegroundColor Cyan
        $n8nScript = Join-Path $ScbeRoot "workflows\n8n\start_n8n_local.ps1"
        if (Test-Path $n8nScript) {
            & $n8nScript
        } else {
            Write-Host "n8n start script not found" -ForegroundColor Red
        }
    }
}

# Ensure artifacts directory exists
$artifactDir = Join-Path $ScbeRoot "artifacts\research"
if (-not (Test-Path $artifactDir)) {
    New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
    Write-Host "Created artifacts/research/" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== HYDRA Research Stack Ready ===" -ForegroundColor Green
Write-Host "Use /research in Claude Code to start a governed research task."
Write-Host "Use /hydra-status for live diagnostics."
