param(
    [string]$TaskName = "SCBE-Colab-Bridge",
    [string]$Profile = "colab_local",
    [int]$Port = 8888,
    [string]$Token = "scbe-local-bridge",
    [string]$NotebookDir = "C:\Users\issda",
    [switch]$UseStartupFolder,
    [switch]$NoScheduledTask
)

$ErrorActionPreference = "Stop"

$root = "C:\Users\issda\SCBE-AETHERMOORE"
$script = Join-Path $root "skills\clawhub\scbe-colab-n8n-bridge\scripts\activate_colab_runtime.ps1"
$batch = Join-Path $root "skills\clawhub\scbe-colab-n8n-bridge\scripts\start_colab_bridge.bat"

if (-not (Test-Path $script)) { throw "Activate script missing: $script" }

function Install-StartupFolderShortcut {
    $startup = [Environment]::GetFolderPath('Startup')
    if (-not (Test-Path $startup)) {
        throw "Startup folder not found: $startup"
    }
    Copy-Item -Path $batch -Destination (Join-Path $startup "start_colab_bridge.bat") -Force
    Write-Host "Installed startup batch at: $startup\start_colab_bridge.bat"
}

function Install-ScheduledTask {
    $arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Profile `"$Profile`" -Port $Port -Token `"$Token`" -NotebookDir `"$NotebookDir`""
    $action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\WindowsPowerShell\v1.0\pwsh.exe" -Argument $arg
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType InteractiveToken -RunLevel Highest
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
    Write-Host "Scheduled task installed: $TaskName"
    Write-Host "Run: Start-ScheduledTask -TaskName `"$TaskName`""
}

if ($UseStartupFolder -or $NoScheduledTask) {
    Install-StartupFolderShortcut
}

if (-not $NoScheduledTask) {
    Install-ScheduledTask
}

Write-Host "Done."
