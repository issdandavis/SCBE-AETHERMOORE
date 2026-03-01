param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$ComposeFile = "",
    [int]$GatewayPort = 18789,
    [int]$BridgePort = 18790,
    [string]$GatewayBind = "lan",
    [string]$GatewayToken = "",
    [string]$OpenClawConfigDir = "",
    [string]$OpenClawWorkspaceDir = "",
    [string]$ImageName = "openclaw:local",
    [int]$StartupTimeoutSec = 30,
    [switch]$HealthCheck
)

$ErrorActionPreference = "Stop"
$InformationPreference = "Continue"

Set-Location $ProjectRoot

if (-not $ComposeFile) {
    $ComposeFile = Join-Path $ProjectRoot "external\openclaw\docker-compose.yml"
}
$defaultComposeDir = Split-Path -Parent $ComposeFile
if (-not (Test-Path $ComposeFile)) {
    if ($defaultComposeDir -and (Test-Path (Join-Path $ProjectRoot "scripts\system\bootstrap_openclaw_sources.ps1"))) {
        & (Join-Path $ProjectRoot "scripts\system\bootstrap_openclaw_sources.ps1") `
            -ProjectRoot $ProjectRoot `
            -OpenClawSourceDir $defaultComposeDir
    }
    if (-not (Test-Path $ComposeFile)) {
        throw "OpenClaw docker-compose file not found: $ComposeFile"
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker executable not found. Install Docker Desktop before starting OpenClaw."
}
if (-not (docker compose version 2>$null | Out-Null; $LASTEXITCODE -eq 0)) {
    throw "Docker Compose plugin not available. Install a Docker Desktop version that supports `docker compose`."
}

if (-not $OpenClawConfigDir) {
    $OpenClawConfigDir = Join-Path $env:USERPROFILE ".openclaw"
}
if (-not $OpenClawWorkspaceDir) {
    $OpenClawWorkspaceDir = Join-Path $OpenClawConfigDir "workspace"
}

New-Item -ItemType Directory -Force -Path $OpenClawConfigDir | Out-Null
New-Item -ItemType Directory -Force -Path $OpenClawWorkspaceDir | Out-Null

if (-not $GatewayToken) {
    $GatewayToken = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")).Substring(0, 64)
}

if (-not $env:OPENCLAW_CONFIG_DIR) { $env:OPENCLAW_CONFIG_DIR = $OpenClawConfigDir }
if (-not $env:OPENCLAW_WORKSPACE_DIR) { $env:OPENCLAW_WORKSPACE_DIR = $OpenClawWorkspaceDir }
$env:OPENCLAW_GATEWAY_TOKEN = $GatewayToken
$env:OPENCLAW_GATEWAY_PORT = "$GatewayPort"
$env:OPENCLAW_BRIDGE_PORT = "$BridgePort"
$env:OPENCLAW_GATEWAY_BIND = $GatewayBind
$env:OPENCLAW_IMAGE = $ImageName

Write-Host "Starting OpenClaw Gateway"
Write-Host "  compose: $ComposeFile"
Write-Host "  gateway port: $GatewayPort"
Write-Host "  bridge port: $BridgePort"
Write-Host "  bind: $GatewayBind"
Write-Host "  image: $ImageName"

$composeArgs = @("-f", $ComposeFile)
if ($ImageName -eq "openclaw:local") {
    Write-Host "Checking OpenClaw image $ImageName..."
    $hasImage = $true
    try {
        docker image inspect $ImageName *> $null
        $hasImage = $true
    } catch {
        $hasImage = $false
    }
    if (-not $hasImage) {
        Write-Host "  building openclaw:local via docker compose"
        docker compose @composeArgs up -d --build openclaw-gateway
    } else {
        docker compose @composeArgs up -d openclaw-gateway
    }
} else {
    docker compose @composeArgs up -d openclaw-gateway
}

if (-not $HealthCheck) {
    return
}

Write-Host "Waiting for gateway health check..."
$deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
do {
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$GatewayPort/health" -TimeoutSec 4
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            Write-Host "OpenClaw health check OK ($($resp.StatusCode))"
            return
        }
        Write-Host "  ... health probe returned $($resp.StatusCode)"
    } catch {
        Write-Host "  ... waiting for health endpoint"
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

throw "OpenClaw gateway did not become healthy within $StartupTimeoutSec seconds."
