param(
    [string]$TaskName = "SCBE-Colab-Bridge",
    [switch]$RemoveStartupBatch
)

$ErrorActionPreference = "SilentlyContinue"

$batchPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\start_colab_bridge.bat"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task: $TaskName"
} else {
    Write-Host "No scheduled task found: $TaskName"
}

if ($RemoveStartupBatch -or (Test-Path $batchPath)) {
    if (Test-Path $batchPath) {
        Remove-Item $batchPath -Force
        Write-Host "Removed startup batch: $batchPath"
    } else {
        Write-Host "Startup batch not present: $batchPath"
    }
}

Write-Host "Done."
