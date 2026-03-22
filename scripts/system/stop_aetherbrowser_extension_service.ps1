param(
    [string]$PidFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($PidFile)) {
    $PidFile = Join-Path $repoRoot "artifacts\system\aetherbrowser_extension_service_pids.json"
}

if (-not (Test-Path $PidFile)) {
    Write-Host "PID snapshot not found: $PidFile" -ForegroundColor Yellow
    return
}

$json = Get-Content -Raw $PidFile | ConvertFrom-Json
$processes = @($json.processes)

if ($processes.Count -eq 0) {
    Write-Host "No processes listed in $PidFile" -ForegroundColor Yellow
    return
}

foreach ($entry in $processes) {
    if ($entry.reused -eq $true) {
        Write-Host ("Skipping reused process: {0}" -f $entry.name) -ForegroundColor DarkGray
        continue
    }
    $procPid = [int]$entry.pid
    if ($procPid -and (Get-Process -Id $procPid -ErrorAction SilentlyContinue)) {
        Write-Host ("Stopping {0} PID {1}" -f $entry.name, $procPid) -ForegroundColor Yellow
        Stop-Process -Id $procPid -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host ("Already stopped: {0} PID {1}" -f $entry.name, $procPid) -ForegroundColor DarkGray
    }
}

Write-Host "AetherBrowser extension service stop complete." -ForegroundColor Green
