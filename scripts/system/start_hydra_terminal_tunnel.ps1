param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [int]$BridgePort = 8002,
    [int]$BrowserPort = 8012,
    [int]$N8nPort = 5680,
    [int]$N8nTaskBrokerPort = 5681,
    [switch]$UseTunnel,
    [switch]$StartOpenClaw,
    [int]$OpenClawGatewayPort = 18789,
    [int]$OpenClawBridgePort = 18790,
    [string]$BrowseUrl = "https://github.com",
    [int]$StartupTimeoutSec = 60
)

$ErrorActionPreference = "Stop"

function Test-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSec = 3
    )
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec -ErrorAction Stop
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSec = 60
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk -Url $Url -TimeoutSec 3) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

Set-Location $RepoRoot

$artifactsDir = Join-Path $RepoRoot "artifacts\system_smoke"
$evidenceDir = Join-Path $RepoRoot "artifacts\page_evidence"
New-Item -ItemType Directory -Force -Path $artifactsDir | Out-Null
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

$bridgeUrl = "http://127.0.0.1:$BridgePort"
$browserUrl = "http://127.0.0.1:$BrowserPort"
$n8nUrl = "http://127.0.0.1:$N8nPort"

$bridgeReady = Test-HttpOk -Url "$bridgeUrl/health"
$browserReady = Test-HttpOk -Url "$browserUrl/health"
$n8nReady = (Test-HttpOk -Url "$n8nUrl/healthz") -or (Test-HttpOk -Url $n8nUrl)

$stackReused = $false
$startedN8nOnly = $false
if ($bridgeReady -and $browserReady -and $n8nReady) {
    Write-Host "HYDRA core stack already healthy; reusing existing services." -ForegroundColor Green
    $stackReused = $true
} elseif ($bridgeReady -and $browserReady -and -not $n8nReady) {
    Write-Host "Bridge+Browser healthy; starting n8n only..." -ForegroundColor Cyan
    $n8nUserFolder = Join-Path $RepoRoot ".n8n_local_iso"
    New-Item -ItemType Directory -Force -Path $n8nUserFolder | Out-Null
    $env:N8N_USER_FOLDER = $n8nUserFolder
    $env:N8N_PORT = "$N8nPort"
    $env:N8N_RUNNERS_BROKER_PORT = "$N8nTaskBrokerPort"
    if (-not $env:N8N_BLOCK_ENV_ACCESS_IN_NODE) {
        $env:N8N_BLOCK_ENV_ACCESS_IN_NODE = "false"
    }

    $n8nCmd = Join-Path $env:APPDATA "npm\n8n.cmd"
    if (-not (Test-Path $n8nCmd)) {
        $n8nCmd = "n8n.cmd"
    }
    $n8nArgs = @("start")
    if ($UseTunnel) {
        $n8nArgs += "--tunnel"
    }
    Start-Process -FilePath $n8nCmd -ArgumentList $n8nArgs -PassThru | Out-Null
    $startedN8nOnly = $true
} else {
    Write-Host "Starting HYDRA core stack..." -ForegroundColor Cyan
    $startScript = Join-Path $RepoRoot "workflows\n8n\start_n8n_local.ps1"
    if (-not (Test-Path $startScript)) {
        throw "Missing stack starter: $startScript"
    }

    $startArgs = @(
        "-ProjectRoot", $RepoRoot,
        "-N8nUserFolder", (Join-Path $RepoRoot ".n8n_local_iso"),
        "-BridgePort", "$BridgePort",
        "-BrowserPort", "$BrowserPort",
        "-N8nPort", "$N8nPort",
        "-N8nTaskBrokerPort", "$N8nTaskBrokerPort",
        "-StartBrowserAgent"
    )

    if ($UseTunnel) {
        $startArgs += "-UseTunnel"
    }
    if ($StartOpenClaw) {
        $startArgs += "-StartOpenClaw"
        $startArgs += @("-OpenClawGatewayPort", "$OpenClawGatewayPort", "-OpenClawBridgePort", "$OpenClawBridgePort")
    }

    & $startScript @startArgs
}

$bridgeReady = Wait-HttpOk -Url "$bridgeUrl/health" -TimeoutSec $StartupTimeoutSec
$browserReady = Wait-HttpOk -Url "$browserUrl/health" -TimeoutSec $StartupTimeoutSec
$n8nReady = (Wait-HttpOk -Url "$n8nUrl/healthz" -TimeoutSec $StartupTimeoutSec) -or (Wait-HttpOk -Url $n8nUrl -TimeoutSec $StartupTimeoutSec)

$smokeOut = Join-Path $artifactsDir "hydra_terminal_tunnel_smoke.json"
python scripts/system/full_system_smoke.py --bridge-url $bridgeUrl --browser-url $browserUrl --n8n-url $n8nUrl --probe-webhook --output $smokeOut
$smokeExit = $LASTEXITCODE

$browseOut = Join-Path $evidenceDir "synthesis_terminal_browse.json"
$browseScript = "C:\Users\issda\.codex\skills\hydra-node-terminal-browsing\scripts\hydra_terminal_browse.mjs"
$browseExit = 0
if (Test-Path $browseScript) {
    node $browseScript --url $BrowseUrl --out $browseOut
    $browseExit = $LASTEXITCODE
} else {
    $browseExit = 1
}

$summary = [ordered]@{
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    stack_reused = $stackReused
    started_n8n_only = $startedN8nOnly
    services = [ordered]@{
        bridge = [ordered]@{ url = "$bridgeUrl/health"; ready = $bridgeReady }
        browser = [ordered]@{ url = "$browserUrl/health"; ready = $browserReady }
        n8n = [ordered]@{ url = "$n8nUrl"; ready = $n8nReady }
    }
    smoke = [ordered]@{
        output = $smokeOut
        exit_code = $smokeExit
    }
    browse = [ordered]@{
        url = $BrowseUrl
        output = $browseOut
        exit_code = $browseExit
    }
}

$summaryOut = Join-Path $artifactsDir "hydra_terminal_tunnel_summary.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryOut -Encoding UTF8
$summary | ConvertTo-Json -Depth 8

if (-not $bridgeReady -or -not $browserReady -or -not $n8nReady -or $smokeExit -ne 0) {
    exit 1
}
exit 0
