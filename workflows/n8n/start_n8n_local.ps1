param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$N8nUserFolder = "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local",
    [int]$BridgePort = 8002,
    [int]$BrowserPort = 8011,
    [int]$N8nPort = 5678,
    [int]$N8nTaskBrokerPort = 0,
    [switch]$ImportWorkflows,
    [switch]$ForceImport,
    [switch]$ResetUserFolder,
    [switch]$PublishWorkflows,
    [switch]$StartBrowserAgent,
    [switch]$UseTunnel
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

# Load .env values into process env (without overriding already-set values)
$dotenvPath = Join-Path $ProjectRoot ".env"
if (Test-Path $dotenvPath) {
    $loadedCount = 0
    foreach ($line in Get-Content $dotenvPath) {
        if (-not $line) { continue }
        $trim = $line.Trim()
        if (-not $trim -or $trim.StartsWith("#")) { continue }
        if ($trim -notmatch "^[A-Za-z_][A-Za-z0-9_]*=") { continue }
        $k, $v = $trim -split "=", 2
        if (-not $k) { continue }
        $current = [Environment]::GetEnvironmentVariable($k, "Process")
        if ([string]::IsNullOrWhiteSpace($current)) {
            [Environment]::SetEnvironmentVariable($k, $v, "Process")
            $loadedCount += 1
        }
    }
    Write-Host "Loaded $loadedCount env var(s) from .env"
}

# n8n workflows in this repo use $env.* expressions in Code/HTTP nodes.
if (-not $env:N8N_BLOCK_ENV_ACCESS_IN_NODE) {
    $env:N8N_BLOCK_ENV_ACCESS_IN_NODE = "false"
}

$env:N8N_USER_FOLDER = $N8nUserFolder
New-Item -ItemType Directory -Force -Path $N8nUserFolder | Out-Null

# Ensure bridge + browser share a compatible API key set.
if (-not $env:SCBE_API_KEYS) {
    $env:SCBE_API_KEYS = "scbe-dev-key,test-key"
}
if (-not $env:SCBE_BROWSER_API_KEY) {
    $firstKey = ($env:SCBE_API_KEYS -split ",")[0].Trim()
    if (-not $firstKey) {
        $firstKey = "scbe-dev-key"
    }
    $env:SCBE_BROWSER_API_KEY = $firstKey
}

# Ensure bridge knows where to forward browser jobs.
if (-not $env:SCBE_BROWSER_SERVICE_URL) {
    $env:SCBE_BROWSER_SERVICE_URL = "http://127.0.0.1:$BrowserPort"
}

if ($ImportWorkflows) {
    & "$ProjectRoot\workflows\n8n\import_workflows.ps1" `
        -ProjectRoot $ProjectRoot `
        -N8nUserFolder $N8nUserFolder `
        -ForceImport:$ForceImport `
        -ResetUserFolder:$ResetUserFolder `
        -PublishWorkflows:$PublishWorkflows
}

Write-Host "Starting SCBE bridge on port $BridgePort"
$bridge = Start-Process -FilePath python -ArgumentList @(
    "-m", "uvicorn",
    "workflows.n8n.scbe_n8n_bridge:app",
    "--host", "127.0.0.1",
    "--port", "$BridgePort"
) -PassThru

Start-Sleep -Seconds 2
try {
    $health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$BridgePort/health" -TimeoutSec 5
    Write-Host "Bridge health status: $($health.StatusCode)"
} catch {
    Write-Warning "Bridge health check failed: $($_.Exception.Message)"
}

$browser = $null
if ($StartBrowserAgent) {
    Write-Host "Starting Browser Agent on port $BrowserPort"
    $browser = Start-Process -FilePath python -ArgumentList @(
        "-m", "uvicorn",
        "agents.browser.main:app",
        "--host", "127.0.0.1",
        "--port", "$BrowserPort"
    ) -PassThru

    Start-Sleep -Seconds 2
    try {
        $browserHealth = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$BrowserPort/health" -TimeoutSec 8
        Write-Host "Browser health status: $($browserHealth.StatusCode)"
    } catch {
        Write-Warning "Browser health check failed: $($_.Exception.Message)"
    }
}

Write-Host "Starting n8n on port $N8nPort"
$env:N8N_PORT = "$N8nPort"
if ($N8nTaskBrokerPort -le 0) {
    $N8nTaskBrokerPort = $N8nPort + 1
}
$env:N8N_RUNNERS_BROKER_PORT = "$N8nTaskBrokerPort"

$n8nCmd = Join-Path $env:APPDATA "npm\n8n.cmd"
if (-not (Test-Path $n8nCmd)) {
    $n8nCmd = "n8n.cmd"
}

$n8nArgs = @("start")
if ($UseTunnel) {
    $n8nArgs += "--tunnel"
}
$n8n = Start-Process -FilePath $n8nCmd -ArgumentList $n8nArgs -PassThru

Start-Sleep -Seconds 3
try {
    $n8nHealth = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$N8nPort/healthz" -TimeoutSec 5
    Write-Host "n8n health status: $($n8nHealth.StatusCode)"
} catch {
    try {
        $n8nRoot = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$N8nPort" -TimeoutSec 5
        Write-Host "n8n root status: $($n8nRoot.StatusCode)"
    } catch {
        Write-Warning "n8n health check failed: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "SCBE n8n local stack running"
Write-Host "Bridge PID: $($bridge.Id)"
if ($browser) {
    Write-Host "Browser PID: $($browser.Id)"
}
Write-Host "n8n PID: $($n8n.Id)"
Write-Host "Bridge URL: http://127.0.0.1:$BridgePort/health"
Write-Host "Browser URL: $($env:SCBE_BROWSER_SERVICE_URL)/health"
Write-Host "n8n URL: http://127.0.0.1:$N8nPort"
if ($UseTunnel) {
    Write-Host "n8n tunnel mode: enabled"
}
Write-Host "n8n task broker port: $N8nTaskBrokerPort"
Write-Host ""
if ($browser) {
    Write-Host "Stop stack: Stop-Process -Id $($bridge.Id),$($browser.Id),$($n8n.Id)"
} else {
    Write-Host "Stop stack: Stop-Process -Id $($bridge.Id),$($n8n.Id)"
}
