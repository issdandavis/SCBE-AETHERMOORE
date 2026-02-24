$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== TEMP FOLDER ==="
$tempPath = "C:\Users\issda\AppData\Local\Temp"
$before = (Get-ChildItem -LiteralPath $tempPath -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Host "Before: $([Math]::Round($before/1GB, 2)) GB"
Get-ChildItem -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
$after = (Get-ChildItem -LiteralPath $tempPath -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Host "After:  $([Math]::Round($after/1GB, 2)) GB"
Write-Host "Freed:  $([Math]::Round(($before - $after)/1GB, 2)) GB"

Write-Host ""
Write-Host "=== NPM CACHE ==="
npm cache clean --force 2>&1 | Write-Host

Write-Host ""
Write-Host "=== PIP CACHE ==="
pip cache purge 2>&1 | Write-Host

Write-Host ""
Write-Host "=== DRIVE STATUS ==="
$drive = Get-PSDrive -Name C
Write-Host "C: Used: $([Math]::Round($drive.Used/1GB, 2)) GB"
Write-Host "C: Free: $([Math]::Round($drive.Free/1GB, 2)) GB"
