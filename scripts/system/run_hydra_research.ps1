# run_hydra_research.ps1 — Orchestration entrypoint for HYDRA Research Stack
# Starts required services and verifies health before enabling research.
param(
    [switch]$StartBridge,
    [switch]$StartOpenClaw,
    [switch]$StartN8n,
    [switch]$HealthOnly,
    [switch]$All
)

$ErrorActionPreference = "Stop"
$ScbeRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$BridgePort = 8002
$BrowserPort = 8012
$N8nPort = 5680
$N8nTaskBrokerPort = 5681
$OpenClawGatewayPort = 18789
$OpenClawBridgePort = 18790
$OpenClawImage = "openclaw:local"

Write-Host "=== HYDRA Research Stack Orchestrator ===" -ForegroundColor Cyan
Write-Host "SCBE Root: $ScbeRoot"
Write-Host ""

# Health check helper
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

Write-Host "--- Service Health ---" -ForegroundColor Yellow
$bridgeUp = Test-ServiceHealth -Name "SCBE Bridge ($BridgePort)" -Url "http://127.0.0.1:$BridgePort/health"
$openclawUp = Test-ServiceHealth -Name "OpenClaw Gateway ($OpenClawGatewayPort)" -Url "http://127.0.0.1:$OpenClawGatewayPort/health"
$n8nUp = Test-ServiceHealth -Name "n8n ($N8nPort)" -Url "http://127.0.0.1:$N8nPort/healthz"
if (-not $n8nUp) {
    $n8nUp = Test-ServiceHealth -Name "n8n ($N8nPort) root" -Url "http://127.0.0.1:$N8nPort"
}

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

if ($All -or $StartBridge -or $StartN8n) {
    Write-Host "Starting SCBE stack (bridge + n8n ...)" -ForegroundColor Cyan
    $startScript = Join-Path $ScbeRoot "workflows\n8n\start_n8n_local.ps1"
    if (Test-Path $startScript) {
        $startArgs = @(
            "-ProjectRoot", $ScbeRoot,
            "-N8nUserFolder", (Join-Path $ScbeRoot ".n8n_local_iso"),
            "-BridgePort", "$BridgePort",
            "-BrowserPort", "$BrowserPort",
            "-N8nPort", "$N8nPort",
            "-N8nTaskBrokerPort", "$N8nTaskBrokerPort"
        )
        if ($All -or $StartBridge) {
            $startArgs += "-StartBrowserAgent"
        }
        if ($All -or $StartOpenClaw) {
            $startArgs += "-StartOpenClaw"
            $startArgs += "-OpenClawGatewayPort", "$OpenClawGatewayPort"
            $startArgs += "-OpenClawBridgePort", "$OpenClawBridgePort"
            $startArgs += "-OpenClawImage", "$OpenClawImage"
        }
        & $startScript @startArgs
        $startedOpenClawViaStack = $true
    } else {
        throw "n8n start script not found: $startScript"
    }
} else {
    $startedOpenClawViaStack = $false
}

if (($All -or $StartOpenClaw) -and -not $startedOpenClawViaStack) {
    Write-Host "Starting OpenClaw Gateway via Docker directly..." -ForegroundColor Cyan
    $openclawScript = Join-Path $ScbeRoot "scripts\system\start_openclaw_gateway.ps1"
    if (Test-Path $openclawScript) {
        & $openclawScript `
            -ProjectRoot $ScbeRoot `
            -ComposeFile (Join-Path $ScbeRoot "external\openclaw\docker-compose.yml") `
            -GatewayPort $OpenClawGatewayPort `
            -BridgePort $OpenClawBridgePort `
            -GatewayBind "lan" `
            -ImageName $OpenClawImage `
            -HealthCheck
    } else {
        Write-Host "OpenClaw starter not found: $openclawScript" -ForegroundColor Red
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
Write-Host "Bridge: http://127.0.0.1:$BridgePort/health"
Write-Host "Browser: http://127.0.0.1:$BrowserPort/health"
Write-Host "n8n: http://127.0.0.1:$N8nPort"
Write-Host "OpenClaw Gateway: http://127.0.0.1:$OpenClawGatewayPort/health"
Write-Host "Use /research in Claude Code to start a governed research task."
Write-Host "Use /hydra-status for live diagnostics."
