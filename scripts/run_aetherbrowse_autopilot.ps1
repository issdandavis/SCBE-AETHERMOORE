param(
    [string]$JobsFile = "examples/aetherbrowse_tasks.sample.json",
    [string]$ApiKey = "",
    [string]$EndpointUrl = "",
    [int]$Concurrency = 3,
    [int]$Port = 8011,
    [switch]$UseLocalService = $true,
    [switch]$NoNoiseOnDeny,
    [string]$OutputJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    if ($env:SCBE_API_KEY) {
        $ApiKey = $env:SCBE_API_KEY.Trim()
    }
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = "0123456789abcdef0123456789abcdef"
}

if ([string]::IsNullOrWhiteSpace($EndpointUrl)) {
    if ($UseLocalService) {
        $EndpointUrl = "http://127.0.0.1:$Port/v1/integrations/n8n/browse"
    } else {
        throw "EndpointUrl is required when -UseLocalService is false."
    }
}

if ([string]::IsNullOrWhiteSpace($OutputJson)) {
    $OutputJson = "artifacts/swarm_autopilot_latest.json"
}

$uvicornProc = $null
if ($UseLocalService) {
    $listenConns = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listenConns) {
        $pids = $listenConns | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $pids) {
            if ($procId) {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Milliseconds 700
    }

    $env:SCBE_API_KEY = $ApiKey
    $env:N8N_API_KEY = $ApiKey
    $uvicornProc = Start-Process -FilePath python `
        -ArgumentList @("-m", "uvicorn", "agents.browser.main:app", "--host", "127.0.0.1", "--port", "$Port") `
        -PassThru -WorkingDirectory $repoRoot -WindowStyle Hidden

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3 | Out-Null
            $ready = $true
            break
        } catch {
        }
    }
    if (-not $ready) {
        if ($uvicornProc -and -not $uvicornProc.HasExited) {
            Stop-Process -Id $uvicornProc.Id -Force -ErrorAction SilentlyContinue
        }
        throw "Local browser service failed to start on port $Port."
    }
}

try {
    $runnerArgs = @(
        "scripts/aetherbrowse_swarm_runner.py",
        "--jobs-file", $JobsFile,
        "--url", $EndpointUrl,
        "--api-key", $ApiKey,
        "--concurrency", "$Concurrency",
        "--save-screenshots-dir", "artifacts/screenshots",
        "--output-json", $OutputJson
    )

    if ($NoNoiseOnDeny) {
        $runnerArgs += "--no-noise-on-deny"
    }

    Write-Host "Running AetherBrowse autopilot..." -ForegroundColor Cyan
    Write-Host ("Jobs: {0}" -f $JobsFile) -ForegroundColor Cyan
    Write-Host ("URL:  {0}" -f $EndpointUrl) -ForegroundColor Cyan
    Write-Host ("Out:  {0}" -f $OutputJson) -ForegroundColor Cyan
    python @runnerArgs
} finally {
    if ($UseLocalService -and $uvicornProc -and -not $uvicornProc.HasExited) {
        Stop-Process -Id $uvicornProc.Id -Force -ErrorAction SilentlyContinue
    }
}
