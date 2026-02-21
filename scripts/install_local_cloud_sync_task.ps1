[CmdletBinding()]
param(
    [string]$TaskName = "SCBE-LocalCloudSync",
    [int]$IntervalMinutes = 2,
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [bool]$RunHidden = $true,
    [string]$ShipTargets = "",
    [switch]$UsePythonW
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be >= 1"
}

$pythonScript = Join-Path $RepoRoot "scripts\local_cloud_autosync.py"
if (-not (Test-Path $pythonScript)) {
    throw "Autosync script not found: $pythonScript"
}

$resolvedUsePythonW = $UsePythonW.IsPresent
if (-not $resolvedUsePythonW) {
    # default to pythonw for no-popup execution
    $resolvedUsePythonW = $true
}

$action = $null
if ($resolvedUsePythonW) {
    $pythonwPath = (Get-Command pythonw.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
    if (-not $pythonwPath) {
        throw "pythonw.exe not found on PATH. Install Python with pythonw or rerun without -UsePythonW."
    }

    $pyArgs = @(
        "`"$pythonScript`"",
        "--config", "training/local_cloud_sync.json",
        "--run-root", "training/runs/local_cloud_sync",
        "--state-file", "training/ingest/local_cloud_sync_state.json",
        "--latest-pointer", "training/ingest/latest_local_cloud_sync.txt",
        "--once"
    )
    if ($ShipTargets -and $ShipTargets.Trim()) {
        $pyArgs += @("--ship-targets", "`"$($ShipTargets.Trim())`"")
    }
    $action = New-ScheduledTaskAction -Execute $pythonwPath -Argument ($pyArgs -join " ") -WorkingDirectory $RepoRoot
}
else {
    $runner = Join-Path $RepoRoot "scripts\run_local_cloud_autosync.ps1"
    if (-not (Test-Path $runner)) {
        throw "Runner script not found: $runner"
    }
    $windowArg = if ($RunHidden) { "-WindowStyle Hidden " } else { "" }
    $targetArg = ""
    if ($ShipTargets -and $ShipTargets.Trim()) {
        $targetArg = " -ShipTargets `"$($ShipTargets.Trim())`""
    }
    $actionArgs = "-NoProfile -NonInteractive ${windowArg}-ExecutionPolicy Bypass -File `"$runner`" -Once$targetArg"
    $action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument $actionArgs -WorkingDirectory $RepoRoot
}
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -Hidden:$RunHidden `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "SCBE local workspace cloud autosync" -Force | Out-Null
Write-Host "Installed scheduled task: $TaskName (every $IntervalMinutes minutes, hidden=$RunHidden, shipTargets='$ShipTargets', mode=$(if($resolvedUsePythonW){'pythonw'}else{'pwsh'}))"
