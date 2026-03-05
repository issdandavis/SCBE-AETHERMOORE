param(
  [ValidateSet("debug", "release")]
  [string]$BuildType = "debug",
  [int]$WaitSeconds = 600,
  [switch]$SkipBuild = $false,
  [switch]$SkipSync = $false,
  [string]$DeviceId = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ToolPath {
  param(
    [string]$Name,
    [string]$FallbackPath = ""
  )

  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  if ($FallbackPath -and (Test-Path $FallbackPath)) {
    return $FallbackPath
  }

  throw "Required command not found: $Name"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$kindleScript = Join-Path $repoRoot "scripts\system\kindle_build_install.ps1"
if (-not (Test-Path $kindleScript)) {
  throw "Missing helper script: $kindleScript"
}

if (-not $env:ANDROID_HOME) {
  $fallbackAndroid = "C:\Users\issda\android-sdk"
  if (Test-Path $fallbackAndroid) { $env:ANDROID_HOME = $fallbackAndroid }
}
if (-not $env:JAVA_HOME) {
  $fallbackJava = "C:\Users\issda\jdk-21\jdk-21.0.10"
  if (Test-Path $fallbackJava) { $env:JAVA_HOME = $fallbackJava }
}

if ($env:ANDROID_HOME) {
  $platformTools = Join-Path $env:ANDROID_HOME "platform-tools"
  if (Test-Path $platformTools) {
    $env:Path = "$platformTools;$env:Path"
  }
}
if ($env:JAVA_HOME) {
  $javaBin = Join-Path $env:JAVA_HOME "bin"
  if (Test-Path $javaBin) {
    $env:Path = "$javaBin;$env:Path"
  }
}

$adb = Resolve-ToolPath -Name "adb" -FallbackPath (Join-Path $env:ANDROID_HOME "platform-tools\adb.exe")
$java = Resolve-ToolPath -Name "java"
$node = Resolve-ToolPath -Name "node"
$npm = Resolve-ToolPath -Name "npm"

Write-Host "Using tools:"
Write-Host "  adb:  $adb"
Write-Host "  java: $java"
Write-Host "  node: $node"
Write-Host "  npm:  $npm"

if (-not $SkipBuild) {
  Write-Host "==> Building Kindle APK..."
  $buildArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $kindleScript,
    "-BuildType", $BuildType
  )
  if ($SkipSync) {
    $buildArgs += "-SkipSync"
  }
  & powershell @buildArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Build step failed."
  }
}

$apkPath = if ($BuildType -eq "release") {
  Join-Path $repoRoot "kindle-app\android\app\build\outputs\apk\release\app-release.apk"
} else {
  Join-Path $repoRoot "kindle-app\android\app\build\outputs\apk\debug\app-debug.apk"
}

if (-not (Test-Path $apkPath)) {
  throw "APK file not found: $apkPath"
}

Write-Host "==> Waiting for USB ADB device (timeout ${WaitSeconds}s)..."
& $adb start-server | Out-Null

$deadline = (Get-Date).AddSeconds($WaitSeconds)
$serial = ""

while ((Get-Date) -lt $deadline) {
  $lines = (& $adb devices) -split "`r?`n"
  if ($DeviceId) {
    $target = $lines | Where-Object { $_ -match "^$([regex]::Escape($DeviceId))\tdevice$" } | Select-Object -First 1
    if ($target) { $serial = $DeviceId; break }
  } else {
    $target = $lines | Where-Object { $_ -match "\tdevice$" } | Select-Object -First 1
    if ($target) {
      $serial = $target.Split("`t")[0]
      break
    }
  }

  $unauthorized = $lines | Where-Object { $_ -match "\tunauthorized$" } | Select-Object -First 1
  if ($unauthorized) {
    Write-Host "Device seen but unauthorized. Unlock Kindle and tap 'Allow USB debugging'."
  }

  Start-Sleep -Seconds 3
}

if (-not $serial) {
  $snapshot = (& $adb devices -l) -join [Environment]::NewLine
  throw "No ADB device became available within timeout. adb devices -l:`n$snapshot"
}

Write-Host "==> Installing APK to $serial..."
& $adb -s $serial install -r $apkPath | Out-Host
if ($LASTEXITCODE -ne 0) {
  throw "ADB install failed."
}

Write-Host "==> Launching app..."
& $adb -s $serial shell monkey -p com.issdandavis.aethercode -c android.intent.category.LAUNCHER 1 | Out-Host

$result = [ordered]@{
  ok = $true
  build_type = $BuildType
  apk_path = $apkPath
  device_id = $serial
  launched = $true
  generated_at = (Get-Date).ToUniversalTime().ToString("o")
}
$result | ConvertTo-Json -Depth 4
