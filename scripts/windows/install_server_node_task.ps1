# Install SCBE Server Node as a Windows Scheduled Task
# Runs on login and restarts on failure
# Run this as Administrator

$repoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) { $pythonExe = "python" }

$taskName = "SCBE-ServerNode"
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "scripts\server_node.py" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed existing task"
}

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "SCBE AetherBrowser server node — runs API + browser tools on login" `
    -RunLevel Highest

Write-Host ""
Write-Host "Installed scheduled task: $taskName"
Write-Host "  Trigger: at logon"
Write-Host "  Action:  python scripts\server_node.py"
Write-Host "  WorkDir: $repoRoot"
Write-Host ""
Write-Host "To start now: Start-ScheduledTask -TaskName $taskName"
Write-Host "To remove:    Unregister-ScheduledTask -TaskName $taskName"
