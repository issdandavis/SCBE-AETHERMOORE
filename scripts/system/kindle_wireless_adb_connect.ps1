param(
  [string]$ConnectEndpoint = "",
  [string]$PairEndpoint = "",
  [string]$PairCode = "",
  [switch]$ShowServicesOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $env:ANDROID_HOME) {
  $fallbackAndroid = "C:\Users\issda\android-sdk"
  if (Test-Path $fallbackAndroid) { $env:ANDROID_HOME = $fallbackAndroid }
}
$adb = if ($env:ANDROID_HOME) { Join-Path $env:ANDROID_HOME "platform-tools\adb.exe" } else { "adb" }
if (-not (Get-Command $adb -ErrorAction SilentlyContinue) -and -not (Test-Path $adb)) {
  throw "adb not found. Set ANDROID_HOME or install platform-tools."
}

& $adb start-server | Out-Null
$services = (& $adb mdns services) -join "`n"

$connectMatch = [regex]::Match($services, '_adb-tls-connect\._tcp\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+)')
$pairMatch = [regex]::Match($services, '_adb-tls-pairing\._tcp\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+)')

if (-not $ConnectEndpoint -and $connectMatch.Success) {
  $ConnectEndpoint = $connectMatch.Groups[1].Value
}
if (-not $PairEndpoint -and $pairMatch.Success) {
  $PairEndpoint = $pairMatch.Groups[1].Value
}

$result = [ordered]@{
  ok = $false
  connect_endpoint = $ConnectEndpoint
  pair_endpoint = $PairEndpoint
  paired = $false
  connected = $false
  devices = @()
  notes = @()
}

if ($ShowServicesOnly) {
  $result.ok = $true
  $result.notes += "mdns services listed only"
  $result.services = $services
  $result | ConvertTo-Json -Depth 6
  exit 0
}

if ($PairEndpoint -and $PairCode) {
  $pairOut = (& $adb pair $PairEndpoint $PairCode) -join "`n"
  if ($pairOut -match 'Successfully paired') {
    $result.paired = $true
  } else {
    $result.notes += "pair_failed: $pairOut"
  }
} elseif ($PairCode -and -not $PairEndpoint) {
  $result.notes += "pair_code_provided_without_pair_endpoint"
}

if ($ConnectEndpoint) {
  $connectOut = (& $adb connect $ConnectEndpoint) -join "`n"
  if ($connectOut -match 'connected to' -or $connectOut -match 'already connected to') {
    $result.connected = $true
  } else {
    $result.notes += "connect_failed: $connectOut"
  }
} else {
  $result.notes += "no_connect_endpoint_discovered"
}

$devLines = (& $adb devices -l) -split "`r?`n"
$result.devices = @($devLines | Where-Object { $_ -match "\tdevice\b" })
$result.ok = $result.connected -or ($result.devices.Count -gt 0)

if (-not $result.ok) {
  $result.notes += "On Kindle open Wireless debugging and use 'Pair device with pairing code', then rerun with -PairEndpoint and -PairCode."
}

$result | ConvertTo-Json -Depth 6
