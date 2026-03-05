param(
    [string]$GatewayHost = "127.0.0.1",
    [int]$GatewayPort = 8400,
    [string]$RuntimeHost = "127.0.0.1",
    [int]$RuntimePort = 8401,
    [switch]$KillOnPortInUse,
    [switch]$HeadlessOnly,
    [switch]$NoWorker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
Set-Location $repoRoot

$pidDir = Join-Path $repoRoot "artifacts\system"
New-Item -ItemType Directory -Path $pidDir -Force | Out-Null
$pidFile = Join-Path $pidDir "aether_native_stack_pids.json"

function Get-ListeningProcessIds {
    param([int]$Port)
    $conns = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @("127.0.0.1", "0.0.0.0", "::", "[::]") }
    if (-not $conns) {
        return @()
    }
    return @($conns | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Stop-ListeningProcesses {
    param([int]$Port)
    $pids = @(Get-ListeningProcessIds -Port $Port)
    foreach ($procId in $pids) {
        if ($procId -and (Get-Process -Id $procId -ErrorAction SilentlyContinue)) {
            Write-Host "Stopping PID $procId on port $Port" -ForegroundColor Yellow
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    if ($pids.Count -gt 0) {
        Start-Sleep -Milliseconds 800
    }
}

function Assert-PortFree {
    param(
        [int]$Port,
        [string]$Label
    )
    $pids = @(Get-ListeningProcessIds -Port $Port)
    if ($pids.Count -gt 0) {
        throw "$Label port $Port is already in use (PID(s): $($pids -join ', ')). Rerun with -KillOnPortInUse or pick a different port."
    }
}

function Wait-HttpReady {
    param(
        [string]$Name,
        [string]$Url,
        [int]$Retries = 60,
        [int]$SleepMs = 500
    )
    for ($i = 0; $i -lt $Retries; $i++) {
        Start-Sleep -Milliseconds $SleepMs
        try {
            Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 3 -ErrorAction Stop | Out-Null
            return
        } catch {
        }
    }
    throw "$Name did not become ready at $Url"
}

if ($KillOnPortInUse) {
    Stop-ListeningProcesses -Port $GatewayPort
    if ($RuntimePort -ne $GatewayPort) {
        Stop-ListeningProcesses -Port $RuntimePort
    }
}

Assert-PortFree -Port $GatewayPort -Label "Gateway"
Assert-PortFree -Port $RuntimePort -Label "Runtime"

$started = @()

try {
    $gatewayProc = Start-Process -FilePath "python" `
        -ArgumentList @("-m", "uvicorn", "src.aethercode.gateway:app", "--host", $GatewayHost, "--port", "$GatewayPort") `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden `
        -PassThru
    $started += [ordered]@{
        name = "gateway"
        pid = $gatewayProc.Id
        url = "http://$GatewayHost`:$GatewayPort"
    }
    Wait-HttpReady -Name "Gateway" -Url "http://$GatewayHost`:$GatewayPort/health"

    $runtimeProc = Start-Process -FilePath "python" `
        -ArgumentList @("-m", "uvicorn", "aetherbrowse.runtime.server:app", "--host", $RuntimeHost, "--port", "$RuntimePort") `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden `
        -PassThru
    $started += [ordered]@{
        name = "runtime"
        pid = $runtimeProc.Id
        url = "http://$RuntimeHost`:$RuntimePort"
    }
    Wait-HttpReady -Name "Runtime" -Url "http://$RuntimeHost`:$RuntimePort/health"

    if (-not $NoWorker) {
        $workerEnv = @{
            AETHERBROWSE_RUNTIME_WS_URL = "ws://$RuntimeHost`:$RuntimePort/ws/worker"
            AETHERBROWSE_RUNTIME_HOST = $RuntimeHost
            AETHERBROWSE_RUNTIME_PORT = "$RuntimePort"
        }
        $workerProc = Start-Process -FilePath "python" `
            -ArgumentList @("aetherbrowse/worker/browser_worker.py") `
            -WorkingDirectory $repoRoot `
            -WindowStyle Hidden `
            -Environment $workerEnv `
            -PassThru
        $started += [ordered]@{
            name = "worker"
            pid = $workerProc.Id
            url = "ws://$RuntimeHost`:$RuntimePort/ws/worker"
        }

        $workerConnected = $false
        for ($i = 0; $i -lt 40; $i++) {
            Start-Sleep -Milliseconds 500
            if ($workerProc.HasExited) {
                throw "Playwright worker exited before connecting to runtime."
            }
            try {
                $health = Invoke-RestMethod -Method Get -Uri "http://$RuntimeHost`:$RuntimePort/health" -TimeoutSec 3 -ErrorAction Stop
                if ($health.worker -eq $true) {
                    $workerConnected = $true
                    break
                }
            } catch {
            }
        }
        if (-not $workerConnected) {
            Write-Warning "Runtime is up, but Playwright worker did not report connected yet."
        }
    }

    if (-not $HeadlessOnly) {
        $electronEnv = @{
            AETHERBROWSE_RUNTIME_HOST = $RuntimeHost
            AETHERBROWSE_RUNTIME_PORT = "$RuntimePort"
        }
        $electronProc = Start-Process -FilePath "npm" `
            -ArgumentList @("run", "dev") `
            -WorkingDirectory (Join-Path $repoRoot "aetherbrowse") `
            -Environment $electronEnv `
            -PassThru
        $started += [ordered]@{
            name = "electron"
            pid = $electronProc.Id
            url = "ws://$RuntimeHost`:$RuntimePort/ws"
        }
    }

    $snapshot = [ordered]@{
        started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        repo_root = $repoRoot
        gateway = "http://$GatewayHost`:$GatewayPort"
        runtime = "http://$RuntimeHost`:$RuntimePort"
        headless_only = [bool]$HeadlessOnly
        worker_enabled = -not [bool]$NoWorker
        processes = $started
    }
    $snapshot | ConvertTo-Json -Depth 8 | Set-Content -Path $pidFile -Encoding UTF8

    Write-Host "Aether native stack started." -ForegroundColor Green
    foreach ($item in $started) {
        Write-Host (" - {0}: PID {1} ({2})" -f $item.name, $item.pid, $item.url) -ForegroundColor Cyan
    }
    Write-Host "PID snapshot: $pidFile" -ForegroundColor Gray
    Write-Host "Gateway health: http://$GatewayHost`:$GatewayPort/health" -ForegroundColor Gray
    Write-Host "Runtime health: http://$RuntimeHost`:$RuntimePort/health" -ForegroundColor Gray
} catch {
    foreach ($entry in $started) {
        $procPid = $entry.pid
        if ($procPid -and (Get-Process -Id $procPid -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $procPid -Force -ErrorAction SilentlyContinue
        }
    }
    throw
}
