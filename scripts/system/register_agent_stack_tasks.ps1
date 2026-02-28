param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$N8nUserFolder = "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso",
    [int]$BridgePort = 8002,
    [int]$BrowserPort = 8012,
    [int]$N8nPort = 5680,
    [int]$N8nTaskBrokerPort = 5681,
    [int]$WatchdogMinutes = 5,
    [string]$TaskPrefix = "SCBE-AgentStack"
)

$ErrorActionPreference = "Stop"

$startScript = Join-Path $ProjectRoot "workflows\n8n\start_n8n_local.ps1"
$watchdogScript = Join-Path $ProjectRoot "scripts\system\watchdog_agent_stack.ps1"

if (-not (Test-Path $startScript)) {
    throw "Missing start script: $startScript"
}
if (-not (Test-Path $watchdogScript)) {
    throw "Missing watchdog script: $watchdogScript"
}

$bootName = "$TaskPrefix-Boot"
$watchdogName = "$TaskPrefix-Watchdog"

$bootArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`" -ProjectRoot `"$ProjectRoot`" -N8nUserFolder `"$N8nUserFolder`" -BridgePort $BridgePort -BrowserPort $BrowserPort -N8nPort $N8nPort -N8nTaskBrokerPort $N8nTaskBrokerPort -StartBrowserAgent"
$watchdogArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogScript`" -ProjectRoot `"$ProjectRoot`" -N8nUserFolder `"$N8nUserFolder`" -BridgePort $BridgePort -BrowserPort $BrowserPort -N8nPort $N8nPort -N8nTaskBrokerPort $N8nTaskBrokerPort"

$registeredVia = "ScheduledTasks"
try {
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1)
    $principal = New-ScheduledTaskPrincipal -UserId "$env:UserDomain\$env:UserName" -LogonType Interactive -RunLevel Highest

    Write-Host "Registering task: $bootName"
    $bootAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $bootArgs
    $bootTrigger = New-ScheduledTaskTrigger -AtLogOn
    Register-ScheduledTask `
        -TaskName $bootName `
        -Action $bootAction `
        -Trigger $bootTrigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Boot SCBE n8n + bridge + browser stack on user logon." `
        -Force | Out-Null

    Write-Host "Registering task: $watchdogName"
    $watchdogAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $watchdogArgs
    $watchdogTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
    $watchdogTrigger.Repetition.Interval = (New-TimeSpan -Minutes $WatchdogMinutes)
    $watchdogTrigger.Repetition.Duration = (New-TimeSpan -Days 3650)
    Register-ScheduledTask `
        -TaskName $watchdogName `
        -Action $watchdogAction `
        -Trigger $watchdogTrigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Watchdog for SCBE stack health; restarts on failure." `
        -Force | Out-Null
} catch {
    Write-Warning "Register-ScheduledTask failed ($($_.Exception.Message)). Falling back to schtasks."
    $registeredVia = "schtasks"

    $bootDefaultScript = Join-Path $ProjectRoot "scripts\system\start_agent_stack_default.ps1"
    $watchdogDefaultScript = Join-Path $ProjectRoot "scripts\system\watchdog_agent_stack_default.ps1"
    if (-not (Test-Path $bootDefaultScript)) {
        throw "Missing fallback start script: $bootDefaultScript"
    }
    if (-not (Test-Path $watchdogDefaultScript)) {
        throw "Missing fallback watchdog script: $watchdogDefaultScript"
    }

    $bootCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$bootDefaultScript`""
    $watchdogCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$watchdogDefaultScript`""

    Write-Host "Registering task via schtasks: $bootName"
    schtasks /Create /TN $bootName /SC ONLOGON /TR $bootCmd /RL HIGHEST /F | Out-Null
    $bootExit = $LASTEXITCODE

    Write-Host "Registering task via schtasks: $watchdogName"
    schtasks /Create /TN $watchdogName /SC MINUTE /MO $WatchdogMinutes /TR $watchdogCmd /RL HIGHEST /F | Out-Null
    $watchdogExit = $LASTEXITCODE

    if ($bootExit -ne 0 -or $watchdogExit -ne 0) {
        Write-Warning "schtasks registration failed (boot=$bootExit watchdog=$watchdogExit). Falling back to Startup folder launchers."
        $registeredVia = "startup-folder"
        $startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
        New-Item -ItemType Directory -Force -Path $startupDir | Out-Null

        $bootLauncher = Join-Path $startupDir "$bootName.cmd"
        $loopScript = Join-Path $ProjectRoot "scripts\system\run_watchdog_loop.ps1"
        $watchdogLauncher = Join-Path $startupDir "$watchdogName.cmd"

        $bootLauncherText = '@echo off' + "`r`n" + 'start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $bootDefaultScript + '"' + "`r`n"
        $watchdogLauncherText = '@echo off' + "`r`n" + 'start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $loopScript + '" -IntervalMinutes ' + $WatchdogMinutes + ' -ProjectRoot "' + $ProjectRoot + '"' + "`r`n"

        Set-Content -Path $bootLauncher -Value $bootLauncherText -Encoding ASCII
        Set-Content -Path $watchdogLauncher -Value $watchdogLauncherText -Encoding ASCII
    }
}

Write-Host ""
Write-Host "Registered tasks:"
if ($registeredVia -eq "ScheduledTasks") {
    Get-ScheduledTask -TaskName $bootName | Format-List TaskName,State,Author,Description
    Get-ScheduledTask -TaskName $watchdogName | Format-List TaskName,State,Author,Description
} else {
    if ($registeredVia -eq "schtasks") {
        schtasks /Query /TN $bootName /FO LIST
        schtasks /Query /TN $watchdogName /FO LIST
    } else {
        $startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
        Get-Item (Join-Path $startupDir "$bootName.cmd") | Format-List FullName,Length,LastWriteTime
        Get-Item (Join-Path $startupDir "$watchdogName.cmd") | Format-List FullName,Length,LastWriteTime
    }
}

Write-Host ""
Write-Host "To remove tasks:"
Write-Host "schtasks /Delete /TN $bootName /F"
Write-Host "schtasks /Delete /TN $watchdogName /F"
