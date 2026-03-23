param(
  [string]$AvdName = "SCBE_Pixel_6_API35",
  [int]$BootTimeoutSec = 420,
  [int]$GatewayPort = 8400,
  [int]$WebPort = 8088,
  [string]$PhoneModeLanIp = "10.0.2.2",
  [string]$PackageName = "com.issdandavis.aethercode",
  [ValidateSet("native", "roomy", "reading", "dashboard")]
  [string]$ScreenPreset = "reading",
  [string]$RuntimeSize = "",
  [int]$RuntimeDensity = 0,
  [double]$FontScale = 0,
  [string]$GpuMode = "auto",
  [string]$SkinSize = "540x1200",
  [int]$PersistCpuCores = 0,
  [int]$PersistRamMB = 0,
  [int]$PersistWidth = 0,
  [int]$PersistHeight = 0,
  [int]$PersistDensity = 0,
  [string[]]$LaunchRoutes = @("/polly-pad.html"),
  [string[]]$ExtraApkPaths = @(),
  [switch]$SkipPhoneMode,
  [switch]$SkipEmulatorLaunch,
  [switch]$SkipInstallApp,
  [switch]$SkipBrowserLaunch,
  [switch]$SkipDeviceTuning,
  [switch]$BuildAppIfMissing,
  [switch]$ColdBoot,
  [switch]$WipeData,
  [switch]$UseSnapshotLoad,
  [switch]$Headless,
  [switch]$HideDeviceFrame,
  [switch]$PreviewOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$statusDir = Join-Path $repoRoot "artifacts\kindle\emulator"
New-Item -ItemType Directory -Path $statusDir -Force | Out-Null
$statusPath = Join-Path $statusDir ("polly_pad_emulator_" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + ".json")

function Resolve-ExistingPath {
  param(
    [string[]]$Candidates,
    [string]$Label
  )

  foreach ($candidate in $Candidates) {
    if ($candidate -and (Test-Path $candidate)) {
      return (Resolve-Path $candidate).Path
    }
  }

  throw "Unable to resolve $Label. Checked: $($Candidates -join ', ')"
}

function Resolve-AndroidSdkRoot {
  $candidates = @(
    $env:ANDROID_SDK_ROOT,
    $env:ANDROID_HOME,
    "C:\Users\issda\AppData\Local\Android\Sdk",
    "C:\Users\issda\android-sdk"
  ) | Where-Object { $_ }

  return Resolve-ExistingPath -Candidates $candidates -Label "Android SDK root"
}

function Resolve-AndroidAvdHome {
  $candidates = @(
    $env:ANDROID_AVD_HOME,
    (Join-Path $env:USERPROFILE ".android\avd"),
    "C:\Users\issda\.android\avd"
  ) | Where-Object { $_ }

  return Resolve-ExistingPath -Candidates $candidates -Label "Android AVD home"
}

function Get-PresetValues {
  param([string]$Preset)

  switch ($Preset) {
    "native" {
      return [ordered]@{ density = 0; fontScale = 1.00 }
    }
    "reading" {
      return [ordered]@{ density = 340; fontScale = 1.12 }
    }
    "dashboard" {
      return [ordered]@{ density = 320; fontScale = 1.00 }
    }
    default {
      return [ordered]@{ density = 360; fontScale = 1.08 }
    }
  }
}

function Set-IniValue {
  param(
    [string]$Path,
    [string]$Key,
    [string]$Value
  )

  $lines = if (Test-Path $Path) { @(Get-Content $Path) } else { @() }
  $pattern = '^' + [regex]::Escape($Key) + '='
  $updated = $false

  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match $pattern) {
      $lines[$i] = "$Key=$Value"
      $updated = $true
    }
  }

  if (-not $updated) {
    $lines += "$Key=$Value"
  }

  Set-Content -Path $Path -Value $lines -Encoding UTF8
}

function Save-Status {
  param([hashtable]$Payload)

  $Payload.generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  $Payload | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
}

function Invoke-AdbRaw {
  param([string[]]$Args)

  $output = & $script:adbPath @Args 2>&1
  return [ordered]@{
    exit_code = $LASTEXITCODE
    output = @($output)
  }
}

function Invoke-Adb {
  param(
    [string[]]$Args,
    [string]$Label = "adb",
    [switch]$AllowFailure
  )

  $result = Invoke-AdbRaw -Args $Args
  if ($result.exit_code -ne 0 -and -not $AllowFailure) {
    throw "$Label failed: $($result.output -join ' ')"
  }
  if ($result.exit_code -ne 0 -and $AllowFailure) {
    $script:state.notes += "$Label failed: $($result.output -join ' ')"
  }
  return $result.output
}

function Get-OnlineEmulatorSerial {
  $null = Invoke-AdbRaw -Args @("start-server")
  $result = Invoke-AdbRaw -Args @("devices", "-l")
  if ($result.exit_code -ne 0) {
    throw "adb devices failed: $($result.output -join ' ')"
  }

  $line = $result.output |
    Where-Object { $_ -match '^emulator-\d+\s+device\b' } |
    Select-Object -First 1

  if (-not $line) { return "" }
  return (($line -split '\s+')[0]).Trim()
}

function Wait-ForBootedEmulator {
  param([int]$TimeoutSec)

  $deadline = (Get-Date).AddSeconds($TimeoutSec)

  while ((Get-Date) -lt $deadline) {
    $serial = ""
    try {
      $serial = Get-OnlineEmulatorSerial
    } catch {
      Start-Sleep -Seconds 2
      continue
    }

    if ($serial) {
      $boot = (Invoke-AdbRaw -Args @("-s", $serial, "shell", "getprop", "sys.boot_completed")).output -join ""
      if ($boot.Trim() -eq "1") {
        return $serial
      }
    }

    Start-Sleep -Seconds 3
  }

  throw "Timed out waiting for emulator '$AvdName' to boot."
}

function Resolve-RouteUrl {
  param([string]$Route)

  if ($Route -match '^https?://') {
    return $Route
  }

  $trimmed = $Route.Trim()
  if (-not $trimmed) {
    return ""
  }

  if ($trimmed.StartsWith("./")) {
    $trimmed = $trimmed.Substring(1)
  }
  if (-not $trimmed.StartsWith("/")) {
    $trimmed = "/" + $trimmed
  }

  return "http://10.0.2.2:$WebPort$trimmed"
}

function Expand-FlatListValues {
  param([string[]]$Values)

  $expanded = New-Object System.Collections.Generic.List[string]
  foreach ($value in @($Values)) {
    if (-not $value) { continue }

    $parts = @($value -split '\s*,\s*')
    foreach ($part in $parts) {
      $clean = $part.Trim().Trim("'").Trim('"')
      if ($clean) {
        $expanded.Add($clean)
      }
    }
  }

  return @($expanded.ToArray())
}

function Apply-BestEffortDeviceSetting {
  param(
    [string[]]$Args,
    [string]$Label
  )

  Invoke-Adb -Args $Args -Label $Label -AllowFailure | Out-Null
}

$androidSdkRoot = Resolve-AndroidSdkRoot
$androidAvdHome = Resolve-AndroidAvdHome
$androidUserHome = Split-Path (Split-Path $androidAvdHome -Parent) -Parent

$script:adbPath = Resolve-ExistingPath -Candidates @(
  (Join-Path $androidSdkRoot "platform-tools\adb.exe"),
  "C:\Users\issda\AppData\Local\Android\Sdk\platform-tools\adb.exe",
  "C:\Users\issda\android-sdk\platform-tools\adb.exe"
) -Label "adb"

$emulatorPath = Resolve-ExistingPath -Candidates @(
  (Join-Path $androidSdkRoot "emulator\emulator.exe"),
  "C:\Users\issda\AppData\Local\Android\Sdk\emulator\emulator.exe"
) -Label "emulator"

$avdConfigPath = Join-Path $androidAvdHome "$AvdName.avd\config.ini"
if (-not (Test-Path $avdConfigPath)) {
  throw "AVD config not found: $avdConfigPath"
}

$preset = Get-PresetValues -Preset $ScreenPreset
$effectiveRuntimeDensity = if ($RuntimeDensity -gt 0) { $RuntimeDensity } else { [int]$preset.density }
$effectiveFontScale = if ($FontScale -gt 0) { $FontScale } else { [double]$preset.fontScale }

$script:state = [ordered]@{
  ok = $false
  mode = if ($PreviewOnly) { "preview_only" } else { "running" }
  repo_root = $repoRoot
  avd_name = $AvdName
  avd_config = $avdConfigPath
  status_file = $statusPath
  android_sdk_root = $androidSdkRoot
  android_avd_home = $androidAvdHome
  android_user_home = $androidUserHome
  emulator_path = $emulatorPath
  adb_path = $script:adbPath
  emulator_pid = $null
  serial = ""
  phone_mode_started = $false
  installed_apks = @()
  launched_urls = @()
  persistent_config_changes = [ordered]@{}
  runtime_tweaks = [ordered]@{
    preset = $ScreenPreset
    size = $RuntimeSize
    density = $effectiveRuntimeDensity
    font_scale = $effectiveFontScale
    gpu_mode = $GpuMode
    skin_size = $SkinSize
  }
  notes = @()
}

Save-Status -Payload $script:state

if ($PersistCpuCores -gt 0) {
  Set-IniValue -Path $avdConfigPath -Key "hw.cpu.ncore" -Value "$PersistCpuCores"
  $script:state.persistent_config_changes["hw.cpu.ncore"] = $PersistCpuCores
}

if ($PersistRamMB -gt 0) {
  Set-IniValue -Path $avdConfigPath -Key "hw.ramSize" -Value "$PersistRamMB"
  $heapSize = [Math]::Max(256, [Math]::Min(1024, [int]($PersistRamMB / 8)))
  Set-IniValue -Path $avdConfigPath -Key "vm.heapSize" -Value "$heapSize"
  $script:state.persistent_config_changes["hw.ramSize"] = $PersistRamMB
  $script:state.persistent_config_changes["vm.heapSize"] = $heapSize
}

if ($PersistWidth -gt 0 -and $PersistHeight -gt 0) {
  Set-IniValue -Path $avdConfigPath -Key "hw.lcd.width" -Value "$PersistWidth"
  Set-IniValue -Path $avdConfigPath -Key "hw.lcd.height" -Value "$PersistHeight"
  Set-IniValue -Path $avdConfigPath -Key "skin.name" -Value ("{0}x{1}" -f $PersistWidth, $PersistHeight)
  $script:state.persistent_config_changes["hw.lcd.width"] = $PersistWidth
  $script:state.persistent_config_changes["hw.lcd.height"] = $PersistHeight
  $script:state.persistent_config_changes["skin.name"] = ("{0}x{1}" -f $PersistWidth, $PersistHeight)
}

if ($PersistDensity -gt 0) {
  Set-IniValue -Path $avdConfigPath -Key "hw.lcd.density" -Value "$PersistDensity"
  $script:state.persistent_config_changes["hw.lcd.density"] = $PersistDensity
}

if ($HideDeviceFrame) {
  Set-IniValue -Path $avdConfigPath -Key "showDeviceFrame" -Value "no"
  $script:state.persistent_config_changes["showDeviceFrame"] = "no"
}

$LaunchRoutes = Expand-FlatListValues -Values $LaunchRoutes
$ExtraApkPaths = Expand-FlatListValues -Values $ExtraApkPaths
$resolvedRoutes = @($LaunchRoutes | ForEach-Object { Resolve-RouteUrl -Route $_ } | Where-Object { $_ })

if ($PreviewOnly) {
  $script:state.ok = $true
  $script:state.launched_urls = $resolvedRoutes
  $script:state.notes += "Preview only. No emulator or adb actions were executed."
  Save-Status -Payload $script:state
  Write-Output ($script:state | ConvertTo-Json -Depth 8)
  exit 0
}

if (-not $SkipPhoneMode) {
  & powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\system\start_aether_phone_mode.ps1") `
    -LanIp $PhoneModeLanIp `
    -GatewayPort $GatewayPort `
    -WebPort $WebPort `
    -KillOnPortInUse | Out-Host
  $script:state.phone_mode_started = $true
  Save-Status -Payload $script:state
}

$serial = ""
try {
  $serial = Get-OnlineEmulatorSerial
  if ($serial) {
    $script:state.notes += "Attached to existing emulator $serial."
  }
} catch {
  $script:state.notes += "Initial adb probe failed: $($_.Exception.Message)"
}

$staleEmulatorProcesses = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
  $_.ProcessName -in @("emulator", "qemu-system-x86_64")
})

if (-not $serial -and $SkipEmulatorLaunch) {
  throw "No ADB-visible emulator is attached. The current session is likely stale. Run scripts/system/stop_polly_pad_emulator.ps1, then relaunch."
}

if (-not $serial -and $staleEmulatorProcesses.Count -gt 0 -and -not $SkipEmulatorLaunch) {
  throw "Found emulator/qemu processes but no ADB-visible emulator. Stop the stale session with scripts/system/stop_polly_pad_emulator.ps1 before launching a fresh AVD."
}

if (-not $serial -and -not $SkipEmulatorLaunch) {
  $emulatorArgs = @("-avd", $AvdName, "-netdelay", "none", "-netspeed", "full", "-gpu", $GpuMode, "-skin", $SkinSize, "-no-boot-anim")
  if (-not $UseSnapshotLoad) { $emulatorArgs += @("-no-snapshot-load") }
  if ($ColdBoot) { $emulatorArgs += @("-no-snapshot") }
  if ($WipeData) { $emulatorArgs += @("-wipe-data") }
  if ($Headless) { $emulatorArgs += @("-no-window") }

  $emuProc = Start-Process -FilePath $emulatorPath -ArgumentList $emulatorArgs -PassThru
  Start-Sleep -Seconds 4
  if ($emuProc.HasExited) {
    throw "Emulator exited immediately with code $($emuProc.ExitCode)."
  }
  $script:state.emulator_pid = $emuProc.Id
}

$serial = Wait-ForBootedEmulator -TimeoutSec $BootTimeoutSec
$script:state.serial = $serial
Save-Status -Payload $script:state

Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP") -Label "wake screen"
Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "wm", "dismiss-keyguard") -Label "dismiss keyguard"

if (-not $SkipDeviceTuning) {
  Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "svc", "power", "stayon", "true") -Label "stay awake"
  Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "settings", "put", "system", "screen_off_timeout", "1800000") -Label "screen timeout"
  Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "settings", "put", "global", "window_animation_scale", "0.0") -Label "window animation scale"
  Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "settings", "put", "global", "transition_animation_scale", "0.0") -Label "transition animation scale"
  Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "settings", "put", "global", "animator_duration_scale", "0.0") -Label "animator duration scale"

  if ($RuntimeSize) {
    Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "wm", "size", $RuntimeSize) -Label "runtime size"
  }
  if ($effectiveRuntimeDensity -gt 0) {
    Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "wm", "density", "$effectiveRuntimeDensity") -Label "runtime density"
  }
  if ($effectiveFontScale -gt 0) {
    Apply-BestEffortDeviceSetting -Args @("-s", $serial, "shell", "settings", "put", "system", "font_scale", "$effectiveFontScale") -Label "font scale"
  }
}

if (-not $SkipInstallApp) {
  $pkgList = (Invoke-Adb -Args @("-s", $serial, "shell", "pm", "list", "packages", $PackageName) -Label "package probe") -join "`n"
  if ($pkgList -notmatch [regex]::Escape($PackageName)) {
    $debugApk = Join-Path $repoRoot "kindle-app\android\app\build\outputs\apk\debug\app-debug.apk"
    if (Test-Path $debugApk) {
      Invoke-Adb -Args @("-s", $serial, "install", "-r", $debugApk) -Label "install AetherCode" | Out-Null
      $script:state.installed_apks += $debugApk
    } elseif ($BuildAppIfMissing) {
      & powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\system\kindle_build_install.ps1") `
        -BuildType debug `
        -Install `
        -DeviceId $serial `
        -SkipSync | Out-Host
    } else {
      $script:state.notes += "AetherCode APK missing at $debugApk. Re-run with -BuildAppIfMissing to build/install."
    }
  }

  Invoke-Adb -Args @("-s", $serial, "shell", "monkey", "-p", $PackageName, "-c", "android.intent.category.LAUNCHER", "1") `
    -Label "launch AetherCode" `
    -AllowFailure | Out-Null

  Save-Status -Payload $script:state
}

foreach ($apk in $ExtraApkPaths) {
  if (-not $apk) { continue }
  $fullPath = if (Test-Path $apk) { (Resolve-Path $apk).Path } else { "" }
  if (-not $fullPath) {
    $script:state.notes += "Skipped missing APK path: $apk"
    continue
  }

  Invoke-Adb -Args @("-s", $serial, "install", "-r", $fullPath) -Label "install extra APK" | Out-Null
  $script:state.installed_apks += $fullPath
  Save-Status -Payload $script:state
}

if (-not $SkipBrowserLaunch) {
  foreach ($url in $resolvedRoutes) {
    $launchOutput = Invoke-Adb -Args @("-s", $serial, "shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", $url) `
      -Label "open route" `
      -AllowFailure
    $script:state.launched_urls += $url
    if (($launchOutput -join " ") -match "FirstRunActivity") {
      $script:state.notes += "Chrome first-run is still active on $serial. Complete it once, then rerun browser-route launch."
      Save-Status -Payload $script:state
      break
    }
    Save-Status -Payload $script:state
    Start-Sleep -Milliseconds 900
  }
}

$script:state.ok = $true
$script:state.mode = "completed"
$script:state.notes += "Persistent CPU/RAM/display changes apply to the AVD profile and may require a relaunch."
$script:state.notes += "Actual performance ceiling still depends on host CPU/GPU and the installed system image."
Save-Status -Payload $script:state
Write-Output ($script:state | ConvertTo-Json -Depth 8)
