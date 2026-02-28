param(
    [int]$IntervalMinutes = 5,
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE"
)

$ErrorActionPreference = "Stop"

$watchdogScript = Join-Path $ProjectRoot "scripts\system\watchdog_agent_stack_default.ps1"
if (-not (Test-Path $watchdogScript)) {
    throw "Missing watchdog default script: $watchdogScript"
}

Write-Host "Starting watchdog loop with interval $IntervalMinutes minute(s)."
while ($true) {
    try {
        & $watchdogScript
    } catch {
        Write-Warning "Watchdog loop iteration failed: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds ([Math]::Max(30, $IntervalMinutes * 60))
}

