$ErrorActionPreference = "Stop"

# Enable OneDrive Files On-Demand via registry
$regPath = 'HKCU:\Software\Microsoft\OneDrive\Accounts\Personal'
if (Test-Path $regPath) {
    Set-ItemProperty -Path $regPath -Name 'FilesOnDemandEnabled' -Value 1 -Type DWord -Force
    Write-Host "Files On-Demand ENABLED at $regPath"
} else {
    Write-Host "Key not found: $regPath"
}

$regPath2 = 'HKCU:\Software\Microsoft\OneDrive'
if (Test-Path $regPath2) {
    Set-ItemProperty -Path $regPath2 -Name 'FilesOnDemandEnabled' -Value 1 -Type DWord -Force
    Write-Host "Files On-Demand ENABLED at $regPath2"
} else {
    Write-Host "Key not found: $regPath2"
}

Write-Host ""
Write-Host "NEXT STEP: Open OneDrive settings (system tray icon > Settings > Sync and backup)"
Write-Host "and confirm 'Files On-Demand' is checked. Then right-click your OneDrive folder"
Write-Host "in Explorer > 'Free up space' to make files cloud-only."
