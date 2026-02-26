$outFile = "C:\Users\issda\SCBE-AETHERMOORE\artifacts\system-audit\disk_check_output.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $outFile) | Out-Null

$sb = [System.Text.StringBuilder]::new()
$null = $sb.AppendLine("=== C: DRIVE ===")
$drive = Get-PSDrive C
$usedGB = [math]::Round($drive.Used / 1GB, 2)
$freeGB = [math]::Round($drive.Free / 1GB, 2)
$totalGB = [math]::Round(($drive.Used + $drive.Free) / 1GB, 2)
$null = $sb.AppendLine("Used: $usedGB GB")
$null = $sb.AppendLine("Free: $freeGB GB")
$null = $sb.AppendLine("Total: $totalGB GB")
$null = $sb.AppendLine("")

$null = $sb.AppendLine("=== SCBE REPO DIRS (top 20) ===")
$dirs = Get-ChildItem 'C:\Users\issda\SCBE-AETHERMOORE' -Directory -ErrorAction SilentlyContinue |
  ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue |
      Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{Name=$_.Name; SizeMB=[math]::Round($size/1MB,1)}
  } | Sort-Object SizeMB -Descending | Select-Object -First 20

foreach ($d in $dirs) {
  $null = $sb.AppendLine("  $($d.SizeMB) MB`t$($d.Name)")
}
$null = $sb.AppendLine("")

$null = $sb.AppendLine("=== USER PROFILE DIRS (top 25) ===")
$pdirs = Get-ChildItem 'C:\Users\issda' -Directory -Force -ErrorAction SilentlyContinue |
  ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue |
      Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{Name=$_.Name; SizeMB=[math]::Round($size/1MB,1)}
  } | Sort-Object SizeMB -Descending | Select-Object -First 25

foreach ($d in $pdirs) {
  $null = $sb.AppendLine("  $($d.SizeMB) MB`t$($d.Name)")
}
$null = $sb.AppendLine("")

$null = $sb.AppendLine("=== SAFE CLEANUP TARGETS ===")
$targets = @(
  'C:\Users\issda\SCBE-AETHERMOORE\.pytest_cache',
  'C:\Users\issda\SCBE-AETHERMOORE\.hypothesis',
  'C:\Users\issda\SCBE-AETHERMOORE\artifacts\pytest_tmp',
  'C:\Users\issda\SCBE-AETHERMOORE\dist',
  'C:\Users\issda\AppData\Local\Temp',
  'C:\Users\issda\AppData\Local\pip\cache',
  'C:\Users\issda\AppData\Local\npm-cache'
)
foreach ($t in $targets) {
  if (Test-Path $t) {
    $size = (Get-ChildItem $t -Recurse -File -ErrorAction SilentlyContinue |
      Measure-Object -Property Length -Sum).Sum
    $sizeMB = [math]::Round($size/1MB,1)
    $null = $sb.AppendLine("  $sizeMB MB`t$t")
  } else {
    $null = $sb.AppendLine("  (not found)`t$t")
  }
}

$sb.ToString() | Set-Content -Path $outFile -Encoding UTF8
Write-Host "Done. Output written to $outFile"
