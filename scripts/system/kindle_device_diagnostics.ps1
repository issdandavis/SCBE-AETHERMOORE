param(
  [string]$Serial = "",
  [string]$PackageName = "com.issdandavis.aethercode"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$outDir = Join-Path $repoRoot "artifacts\kindle\diagnostics"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

if (-not $env:ANDROID_HOME) {
  $fallbackAndroid = "C:\Users\issda\android-sdk"
  if (Test-Path $fallbackAndroid) { $env:ANDROID_HOME = $fallbackAndroid }
}
$adb = if ($env:ANDROID_HOME) { Join-Path $env:ANDROID_HOME "platform-tools\adb.exe" } else { "adb" }
if (-not (Get-Command $adb -ErrorAction SilentlyContinue) -and -not (Test-Path $adb)) {
  throw "adb not found. Set ANDROID_HOME or install platform-tools."
}

function Invoke-Adb {
  param([string[]]$Args)
  if ($Serial) {
    return & $adb -s $Serial @Args
  }
  return & $adb @Args
}

if (-not $Serial) {
  $lines = (& $adb devices) -split "`r?`n"
  $first = $lines | Where-Object { $_ -match "\tdevice$" } | Select-Object -First 1
  if (-not $first) {
    throw "No authorized ADB device found."
  }
  $Serial = $first.Split("`t")[0]
}

$ts = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$prefix = "kindle_diag_$($Serial -replace '[^a-zA-Z0-9_-]','_')_$ts"

$meta = [ordered]@{
  serial = $Serial
  package = $PackageName
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
}

function Save-Output {
  param(
    [string]$Name,
    [string[]]$Args
  )
  $path = Join-Path $outDir "$prefix-$Name.txt"
  $output = Invoke-Adb -Args $Args 2>&1
  $output | Set-Content -Path $path -Encoding UTF8
  return $path
}

$meta.device_model = (Invoke-Adb -Args @("shell", "getprop", "ro.product.model")) -join "`n"
$meta.android_release = (Invoke-Adb -Args @("shell", "getprop", "ro.build.version.release")) -join "`n"
$meta.android_sdk = (Invoke-Adb -Args @("shell", "getprop", "ro.build.version.sdk")) -join "`n"

$paths = [ordered]@{}
$paths.meminfo = Save-Output -Name "meminfo" -Args @("shell", "cat", "/proc/meminfo")
$paths.top = Save-Output -Name "top" -Args @("shell", "top", "-n", "1", "-b")
$paths.battery = Save-Output -Name "battery" -Args @("shell", "dumpsys", "battery")
$paths.cpuinfo = Save-Output -Name "cpuinfo" -Args @("shell", "cat", "/proc/cpuinfo")
$paths.activity = Save-Output -Name "activity-top" -Args @("shell", "dumpsys", "activity", "top")

$pkgCheck = (Invoke-Adb -Args @("shell", "pm", "list", "packages", $PackageName)) -join "`n"
$meta.package_installed = [bool]($pkgCheck -match [regex]::Escape($PackageName))

if ($meta.package_installed) {
  $paths.package_meminfo = Save-Output -Name "package-meminfo" -Args @("shell", "dumpsys", "meminfo", $PackageName)
  $paths.package_gfxinfo = Save-Output -Name "package-gfxinfo" -Args @("shell", "dumpsys", "gfxinfo", $PackageName)
}

$meta.outputs = $paths
$jsonPath = Join-Path $outDir "$prefix-summary.json"
$meta | ConvertTo-Json -Depth 6 | Set-Content -Path $jsonPath -Encoding UTF8

$result = [ordered]@{
  ok = $true
  serial = $Serial
  package = $PackageName
  summary = $jsonPath
  outputs = $paths
}
$result | ConvertTo-Json -Depth 6
