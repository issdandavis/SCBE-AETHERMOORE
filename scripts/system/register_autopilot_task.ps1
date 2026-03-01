<#
.SYNOPSIS
    Register a Windows Task Scheduler job that runs the SCBE ops autopilot every 4 hours.

.DESCRIPTION
    Creates a scheduled task "SCBE-OpsAutopilot" that:
      - Runs scripts/ops_24x7_autopilot.py every 4 hours
      - Uses --iterations 1 (single cycle per trigger)
      - Skips GPU smoke by default (CPU-only, free)
      - Logs to artifacts/ops-autopilot/

.PARAMETER Interval
    Repetition interval in hours (default 4).

.PARAMETER PythonPath
    Path to python.exe. Auto-detected if not provided.

.PARAMETER Unregister
    Remove the scheduled task instead of creating it.

.EXAMPLE
    .\register_autopilot_task.ps1
    .\register_autopilot_task.ps1 -Interval 6
    .\register_autopilot_task.ps1 -Unregister
#>
param(
    [int]$Interval = 4,
    [string]$PythonPath = "",
    [switch]$Unregister,
    [switch]$WithMoney,
    [switch]$WithSmoke,
    [switch]$WithTelegram
)

$ErrorActionPreference = "Stop"
$TaskName = "SCBE-OpsAutopilot"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path

if ($Unregister) {
    Write-Host "Removing scheduled task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Done."
    exit 0
}

# Find Python
if (-not $PythonPath) {
    $PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonPath) {
        $PythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
    }
}
if (-not $PythonPath -or -not (Test-Path $PythonPath)) {
    Write-Error "Cannot find python. Pass -PythonPath explicitly."
    exit 1
}

Write-Host "Python: $PythonPath"
Write-Host "Repo:   $RepoRoot"
Write-Host "Interval: every $Interval hours"

# Build argument list
$ScriptPath = Join-Path $RepoRoot "scripts\ops_24x7_autopilot.py"
$Args = @(
    "`"$ScriptPath`"",
    "--scan-name", "scheduled",
    "--skip-smoke",
    "--repeat-every-minutes", "0",
    "--iterations", "1"
)

if ($WithMoney) {
    $Args += "--run-money"
    $Args += "--money-probe"
}
if ($WithSmoke) {
    # Remove --skip-smoke, add --run-smoke
    $Args = $Args | Where-Object { $_ -ne "--skip-smoke" }
    $Args += "--run-smoke"
}

$ArgString = $Args -join " "

# Create the scheduled task
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument $ArgString `
    -WorkingDirectory $RepoRoot

# Trigger: every N hours, starting now
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours $Interval) `
    -RepetitionDuration (New-TimeSpan -Days 365)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Register (overwrite if exists)
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "SCBE ops autopilot: scan + postprocess + optional money/smoke every ${Interval}h" `
    -Force

Write-Host ""
Write-Host "Scheduled task '$TaskName' registered."
Write-Host "  Runs every $Interval hours"
Write-Host "  Command: $PythonPath $ArgString"
Write-Host "  Working dir: $RepoRoot"
Write-Host ""
Write-Host "To verify:  Get-ScheduledTask -TaskName '$TaskName' | Format-List"
Write-Host "To run now: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove:  .\register_autopilot_task.ps1 -Unregister"
