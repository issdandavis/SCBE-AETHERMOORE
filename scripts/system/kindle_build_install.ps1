param(
  [ValidateSet("debug", "release")]
  [string]$BuildType = "debug",
  [switch]$Install = $false,
  [string]$DeviceId = "",
  [switch]$SkipSync = $false
)

$ErrorActionPreference = "Stop"

function Require-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $Name"
  }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$kindleDir = Join-Path $repoRoot "kindle-app"
if (-not (Test-Path $kindleDir)) {
  throw "kindle-app directory not found at $kindleDir"
}

Require-Command "node"
Require-Command "npm"
Require-Command "java"

if ($Install) {
  Require-Command "adb"
}

Push-Location $kindleDir
try {
  Write-Host "==> Copying and patching PWA assets..."
  npm run copy:assets | Out-Host

  if (-not $SkipSync) {
    Write-Host "==> Syncing Capacitor Android project..."
    if (-not (Test-Path (Join-Path $kindleDir "android"))) {
      npx cap add android | Out-Host
    }
    npx cap sync android | Out-Host
  }

  Write-Host "==> Building APK ($BuildType)..."
  Push-Location (Join-Path $kindleDir "android")
  try {
    if ($BuildType -eq "release") {
      .\gradlew assembleRelease | Out-Host
      if ($LASTEXITCODE -ne 0) {
        throw "Gradle release build failed. Ensure JDK 17 is installed and JAVA_HOME is set."
      }
      $releaseDir = Join-Path (Get-Location) "app\build\outputs\apk\release"
      $preferredRelease = Join-Path $releaseDir "app-release.apk"
      if (Test-Path $preferredRelease) {
        $apkPath = $preferredRelease
      } else {
        $releaseApk = Get-ChildItem -Path $releaseDir -Filter "*.apk" -File -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTimeUtc -Descending |
          Select-Object -First 1
        if (-not $releaseApk) {
          throw "Gradle release build completed but no APK was found in: $releaseDir"
        }
        $apkPath = $releaseApk.FullName
      }
    } else {
      .\gradlew assembleDebug | Out-Host
      if ($LASTEXITCODE -ne 0) {
        throw "Gradle debug build failed. Ensure JDK 17 is installed and JAVA_HOME is set."
      }
      $debugDir = Join-Path (Get-Location) "app\build\outputs\apk\debug"
      $preferredDebug = Join-Path $debugDir "app-debug.apk"
      if (Test-Path $preferredDebug) {
        $apkPath = $preferredDebug
      } else {
        $debugApk = Get-ChildItem -Path $debugDir -Filter "*.apk" -File -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTimeUtc -Descending |
          Select-Object -First 1
        if (-not $debugApk) {
          throw "Gradle debug build completed but no APK was found in: $debugDir"
        }
        $apkPath = $debugApk.FullName
      }
    }
  } finally {
    Pop-Location
  }

  if (-not (Test-Path $apkPath)) {
    throw "APK build completed but file not found: $apkPath"
  }

  $result = [ordered]@{
    ok = $true
    build_type = $BuildType
    apk_path = $apkPath
    installed = $false
    device_id = ""
  }

  if ($Install) {
    Write-Host "==> Checking ADB devices..."
    $adbDevices = adb devices
    $online = $adbDevices | Select-String -Pattern "\sdevice$"
    if (-not $online) {
      throw "No online ADB devices found. Connect Kindle, enable USB debugging, then retry."
    }

    if ($DeviceId) {
      Write-Host "==> Installing APK to device $DeviceId..."
      adb -s $DeviceId install -r $apkPath | Out-Host
      $result.installed = $true
      $result.device_id = $DeviceId
    } else {
      Write-Host "==> Installing APK to first online device..."
      adb install -r $apkPath | Out-Host
      $first = ($online | Select-Object -First 1).Line.Split("`t")[0]
      $result.installed = $true
      $result.device_id = $first
    }
  }

  $json = $result | ConvertTo-Json -Depth 4
  Write-Output $json
}
finally {
  Pop-Location
}
