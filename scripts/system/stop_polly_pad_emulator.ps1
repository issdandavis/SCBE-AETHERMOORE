param(
  [string]$AvdName = "SCBE_Pixel_6_API35",
  [switch]$StopPhoneMode,
  [switch]$StopAdbServer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$statusDir = Join-Path $repoRoot "artifacts\kindle\emulator"
New-Item -ItemType Directory -Path $statusDir -Force | Out-Null
$statusPath = Join-Path $statusDir ("polly_pad_emulator_stop_" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + ".json")

function Save-Status {
  param([hashtable]$Payload)
  $Payload.generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  $Payload | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
}

$result = [ordered]@{
  ok = $false
  avd_name = $AvdName
  status_file = $statusPath
  repo_root = $repoRoot
  stopped = @()
  removed = @()
  notes = @()
}

if ($StopPhoneMode) {
  try {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\system\stop_aether_phone_mode.ps1") | Out-Host
    $result.notes += "Stopped phone mode."
  } catch {
    $result.notes += "Phone mode stop failed: $($_.Exception.Message)"
  }
}

$targets = @("emulator", "qemu-system-x86_64")
if ($StopAdbServer) {
  $targets += "adb"
}

foreach ($proc in (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in $targets })) {
  try {
    Stop-Process -Id $proc.Id -Force -ErrorAction Stop
    $result.stopped += [ordered]@{
      name = $proc.ProcessName
      pid = $proc.Id
    }
  } catch {
    $result.notes += "Failed to stop $($proc.ProcessName) PID $($proc.Id): $($_.Exception.Message)"
  }
}

Start-Sleep -Milliseconds 800

$lockTargets = @(
  "C:\Users\issda\.android\emu-last-feature-flags.protobuf.lock",
  (Join-Path "C:\Users\issda\.android\avd" "$AvdName.avd\multiinstance.lock"),
  (Join-Path "C:\Users\issda\.android\avd" "$AvdName.avd\hardware-qemu.ini.lock")
)

foreach ($target in $lockTargets) {
  if (-not (Test-Path $target)) { continue }
  try {
    Remove-Item -Path $target -Recurse -Force -ErrorAction Stop
    $result.removed += $target
  } catch {
    $result.notes += "Failed to remove lock target $target : $($_.Exception.Message)"
  }
}

$result.ok = $true
Save-Status -Payload $result
Write-Output ($result | ConvertTo-Json -Depth 8)
