param(
  [int]$WaitSeconds = 900,
  [switch]$StartPhoneMode = $true,
  [switch]$InstallApkOnConnect = $true,
  [switch]$RunDiagnosticsOnConnect = $true,
  [string]$PackageName = "com.issdandavis.aethercode"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$statusDir = Join-Path $repoRoot "artifacts\kindle\autopilot"
New-Item -ItemType Directory -Path $statusDir -Force | Out-Null
$statusPath = Join-Path $statusDir ("kindle_autopilot_" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + ".json")

if (-not $env:ANDROID_HOME) {
  $fallbackAndroid = "C:\Users\issda\android-sdk"
  if (Test-Path $fallbackAndroid) { $env:ANDROID_HOME = $fallbackAndroid }
}
$adb = if ($env:ANDROID_HOME) { Join-Path $env:ANDROID_HOME "platform-tools\adb.exe" } else { "adb" }
if (-not (Get-Command $adb -ErrorAction SilentlyContinue) -and -not (Test-Path $adb)) {
  throw "adb not found. Set ANDROID_HOME or install platform-tools."
}

function Get-ConnectedSerial {
  $lines = (& $adb devices) -split "`r?`n"
  $line = $lines | Where-Object { $_ -match "\tdevice$" } | Select-Object -First 1
  if (-not $line) { return "" }
  return $line.Split("`t")[0]
}

function Get-MdnsConnectEndpoint {
  $services = (& $adb mdns services) -join "`n"
  $m = [regex]::Match($services, '_adb-tls-connect\._tcp\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+)')
  if ($m.Success) { return $m.Groups[1].Value }
  return ""
}

function Save-Status {
  param([hashtable]$Payload)
  $Payload.generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  $Payload | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
}

if ($StartPhoneMode) {
  & powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\system\start_aether_phone_mode.ps1") -KillOnPortInUse | Out-Null
}

& $adb start-server | Out-Null

$state = @{
  ok = $false
  mode = "running"
  connect_attempts = 0
  connect_endpoint = ""
  serial = ""
  apk_installed = $false
  diagnostics_ran = $false
  status_file = $statusPath
  notes = @()
}
Save-Status -Payload $state

$deadline = (Get-Date).AddSeconds($WaitSeconds)
while ((Get-Date) -lt $deadline) {
  $serial = Get-ConnectedSerial
  if ($serial) {
    $state.serial = $serial
    $state.ok = $true
    $state.mode = "connected"
    break
  }

  $endpoint = Get-MdnsConnectEndpoint
  if ($endpoint) {
    $state.connect_endpoint = $endpoint
    $state.connect_attempts++
    & $adb connect $endpoint | Out-Null
  } else {
    $state.notes += "mdns_connect_endpoint_not_found"
  }
  Save-Status -Payload $state
  Start-Sleep -Seconds 3
}

if (-not $state.serial) {
  $state.mode = "timeout_no_device"
  $state.notes += "Wireless debug not fully paired. On Kindle use 'Pair device with pairing code'."
  Save-Status -Payload $state
  Write-Output ($state | ConvertTo-Json -Depth 8)
  exit 0
}

if ($InstallApkOnConnect) {
  $apkPath = Join-Path $repoRoot "kindle-app\android\app\build\outputs\apk\debug\app-debug.apk"
  if (Test-Path $apkPath) {
    & $adb -s $state.serial install -r $apkPath | Out-Null
    & $adb -s $state.serial shell monkey -p $PackageName -c android.intent.category.LAUNCHER 1 | Out-Null
    $state.apk_installed = $true
  } else {
    $state.notes += "apk_missing_at_$apkPath"
  }
}

if ($RunDiagnosticsOnConnect) {
  try {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\system\kindle_device_diagnostics.ps1") -Serial $state.serial -PackageName $PackageName | Out-Null
    $state.diagnostics_ran = $true
  } catch {
    $state.notes += "diagnostics_failed: $($_.Exception.Message)"
  }
}

$state.mode = "completed"
Save-Status -Payload $state
Write-Output ($state | ConvertTo-Json -Depth 8)
