param(
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8002,
    [int]$ChromeDebugPort = 9222,
    [string]$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe",
    [string]$PythonExe = "python",
    [string]$UserDataDir = "C:\Users\issda\.scbe-aetherbrowser\profiles\service-main",
    [string]$ExtensionDir = "",
    [string]$StartUrl = "",
    [switch]$KillOnPortInUse,
    [switch]$RunVerify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($ExtensionDir)) {
    $ExtensionDir = (Join-Path $repoRoot "src\extension")
}
if ([string]::IsNullOrWhiteSpace($StartUrl)) {
    $StartUrl = "http://$BackendHost`:$BackendPort/health"
}
New-Item -ItemType Directory -Path $UserDataDir -Force | Out-Null

$artifactsDir = Join-Path $repoRoot "artifacts\system"
$smokeDir = Join-Path $repoRoot "artifacts\smokes"
New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null
New-Item -ItemType Directory -Path $smokeDir -Force | Out-Null
$pidFile = Join-Path $artifactsDir "aetherbrowser_extension_service_pids.json"
$backendOut = Join-Path $smokeDir "aetherbrowser-extension-backend-out.log"
$backendErr = Join-Path $smokeDir "aetherbrowser-extension-backend-err.log"

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
            return Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 3 -ErrorAction Stop
        } catch {
        }
    }
    throw "$Name did not become ready at $Url"
}

function Wait-CdpReady {
    param(
        [int]$Port,
        [int]$Retries = 60,
        [int]$SleepMs = 500
    )
    $url = "http://127.0.0.1:$Port/json/list"
    for ($i = 0; $i -lt $Retries; $i++) {
        Start-Sleep -Milliseconds $SleepMs
        try {
            return Invoke-RestMethod -Method Get -Uri $url -TimeoutSec 3 -ErrorAction Stop
        } catch {
        }
    }
    throw "Chrome CDP did not become ready at $url"
}

if ($KillOnPortInUse) {
    Stop-ListeningProcesses -Port $BackendPort
    if ($ChromeDebugPort -ne $BackendPort) {
        Stop-ListeningProcesses -Port $ChromeDebugPort
    }
}

$started = @()
$backendReused = $false
$chromeReused = $false

try {
    $backendPids = @(Get-ListeningProcessIds -Port $BackendPort)
    if ($backendPids.Count -gt 0) {
        $null = Wait-HttpReady -Name "Backend" -Url "http://$BackendHost`:$BackendPort/health" -Retries 4 -SleepMs 300
        $backendReused = $true
        $started += [ordered]@{
            name = "backend"
            pid = $null
            reused = $true
            url = "http://$BackendHost`:$BackendPort"
        }
    } else {
        $backendProc = Start-Process -FilePath $PythonExe `
            -ArgumentList @("-m", "uvicorn", "src.aetherbrowser.serve:app", "--host", $BackendHost, "--port", "$BackendPort") `
            -WorkingDirectory $repoRoot `
            -RedirectStandardOutput $backendOut `
            -RedirectStandardError $backendErr `
            -PassThru
        $null = Wait-HttpReady -Name "Backend" -Url "http://$BackendHost`:$BackendPort/health"
        $started += [ordered]@{
            name = "backend"
            pid = $backendProc.Id
            reused = $false
            url = "http://$BackendHost`:$BackendPort"
        }
    }

    $chromePids = @(Get-ListeningProcessIds -Port $ChromeDebugPort)
    if ($chromePids.Count -gt 0) {
        $null = Wait-CdpReady -Port $ChromeDebugPort -Retries 4 -SleepMs 300
        $chromeReused = $true
        $started += [ordered]@{
            name = "chrome"
            pid = $null
            reused = $true
            url = "http://127.0.0.1:$ChromeDebugPort/json/list"
        }
    } else {
        $chromeArgs = @(
            "--remote-debugging-port=$ChromeDebugPort",
            "--user-data-dir=$UserDataDir",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
            "--disable-sync",
            "--load-extension=$ExtensionDir",
            "--disable-extensions-except=$ExtensionDir",
            $StartUrl
        )
        $chromeProc = Start-Process -FilePath $ChromePath `
            -ArgumentList $chromeArgs `
            -WorkingDirectory $repoRoot `
            -PassThru
        $null = Wait-CdpReady -Port $ChromeDebugPort
        $started += [ordered]@{
            name = "chrome"
            pid = $chromeProc.Id
            reused = $false
            url = "http://127.0.0.1:$ChromeDebugPort/json/list"
        }
    }

    $snapshot = [ordered]@{
        started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        repo_root = $repoRoot
        backend = "http://$BackendHost`:$BackendPort"
        chrome_debug = "http://127.0.0.1:$ChromeDebugPort/json/list"
        chrome_path = $ChromePath
        extension_dir = $ExtensionDir
        user_data_dir = $UserDataDir
        start_url = $StartUrl
        backend_reused = [bool]$backendReused
        chrome_reused = [bool]$chromeReused
        processes = $started
        logs = [ordered]@{
            backend_stdout = $backendOut
            backend_stderr = $backendErr
        }
    }
    $snapshot | ConvertTo-Json -Depth 8 | Set-Content -Path $pidFile -Encoding UTF8

    Write-Host "AetherBrowser extension service started." -ForegroundColor Green
    foreach ($item in $started) {
        $pidDisplay = if ($null -eq $item.pid) { "reused" } else { "PID $($item.pid)" }
        Write-Host (" - {0}: {1} ({2})" -f $item.name, $pidDisplay, $item.url) -ForegroundColor Cyan
    }
    Write-Host "PID snapshot: $pidFile" -ForegroundColor Gray

    if ($RunVerify) {
        & $PythonExe (Join-Path $repoRoot "scripts\verify_aetherbrowser_extension_service.py") `
            --host $BackendHost `
            --port $BackendPort `
            --chrome-port $ChromeDebugPort `
            --run-backend-smoke `
            --json
    }
} catch {
    foreach ($entry in $started) {
        $procPid = $entry.pid
        if ($procPid -and (Get-Process -Id $procPid -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $procPid -Force -ErrorAction SilentlyContinue
        }
    }
    throw
}
