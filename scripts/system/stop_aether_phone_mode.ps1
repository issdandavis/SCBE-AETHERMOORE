$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$pidFile = Join-Path $repoRoot "artifacts\system\aether_phone_mode_pids.json"

if (-not (Test-Path $pidFile)) {
    Write-Host "No phone-mode PID file found at $pidFile"
    exit 0
}

$json = Get-Content -Path $pidFile -Raw | ConvertFrom-Json
$stopped = @()
foreach ($proc in $json.processes) {
    $procId = [int]$proc.pid
    if ($procId -and (Get-Process -Id $procId -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        $stopped += $proc
    }
}

Remove-Item $pidFile -Force -ErrorAction SilentlyContinue

if ($stopped.Count -eq 0) {
    Write-Host "No running phone-mode processes found."
} else {
    Write-Host "Stopped phone-mode processes:"
    foreach ($p in $stopped) {
        Write-Host (" - {0}: PID {1}" -f $p.name, $p.pid)
    }
}
