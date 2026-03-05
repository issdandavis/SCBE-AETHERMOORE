param(
  [int]$Cycles = 20,
  [int]$WaitSecondsPerCycle = 120,
  [switch]$StartPhoneMode = $true,
  [switch]$InstallApkOnConnect = $true,
  [switch]$RunDiagnosticsOnConnect = $true,
  [string]$PackageName = "com.issdandavis.aethercode"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$outDir = Join-Path $repoRoot "artifacts\kindle\nonstop"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$outPath = Join-Path $outDir ("kindle_nonstop_" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + ".json")

$records = @()
$success = $false

for ($i = 1; $i -le $Cycles; $i++) {
  $entry = [ordered]@{
    cycle = $i
    started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    pair_attempted = $false
    connect_attempted = $false
    connected = $false
    autopilot_ok = $false
    notes = @()
  }

  try {
    if ($env:KINDLE_PAIR_ENDPOINT -and $env:KINDLE_PAIR_CODE) {
      $entry.pair_attempted = $true
      $pairArgs = @(
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $repoRoot "scripts\system\kindle_wireless_adb_connect.ps1"),
        "-PairEndpoint", $env:KINDLE_PAIR_ENDPOINT,
        "-PairCode", $env:KINDLE_PAIR_CODE
      )
      if ($env:KINDLE_CONNECT_ENDPOINT) {
        $pairArgs += @("-ConnectEndpoint", $env:KINDLE_CONNECT_ENDPOINT)
      }
      & powershell @pairArgs | Out-Null
    } else {
      $entry.connect_attempted = $true
      $connectArgs = @(
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $repoRoot "scripts\system\kindle_wireless_adb_connect.ps1")
      )
      if ($env:KINDLE_CONNECT_ENDPOINT) {
        $connectArgs += @("-ConnectEndpoint", $env:KINDLE_CONNECT_ENDPOINT)
      }
      & powershell @connectArgs | Out-Null
    }
  } catch {
    $entry.notes += "wireless_connect_error: $($_.Exception.Message)"
  }

  try {
    $autoArgs = @(
      "-ExecutionPolicy", "Bypass",
      "-File", (Join-Path $repoRoot "scripts\system\kindle_autopilot.ps1"),
      "-WaitSeconds", "$WaitSecondsPerCycle",
      "-PackageName", $PackageName
    )
    if ($StartPhoneMode) { $autoArgs += "-StartPhoneMode" }
    if ($InstallApkOnConnect) { $autoArgs += "-InstallApkOnConnect" }
    if ($RunDiagnosticsOnConnect) { $autoArgs += "-RunDiagnosticsOnConnect" }
    $autoRaw = & powershell @autoArgs
    $autoObj = $null
    try { $autoObj = $autoRaw | ConvertFrom-Json } catch {}
    if ($autoObj) {
      $entry.autopilot_ok = [bool]$autoObj.ok
      $entry.connected = [bool]($autoObj.serial -and $autoObj.serial -ne "")
      $entry.autopilot_mode = $autoObj.mode
      $entry.serial = $autoObj.serial
      if ($autoObj.notes) {
        foreach ($n in $autoObj.notes) { $entry.notes += [string]$n }
      }
    } else {
      $entry.notes += "autopilot_no_json_output"
    }
  } catch {
    $entry.notes += "autopilot_error: $($_.Exception.Message)"
  }

  $entry.finished_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  $records += $entry
  $records | ConvertTo-Json -Depth 8 | Set-Content -Path $outPath -Encoding UTF8

  if ($entry.connected -or $entry.autopilot_ok) {
    $success = $true
    break
  }

  Start-Sleep -Seconds 2
}

$result = [ordered]@{
  ok = $success
  cycles_requested = $Cycles
  cycles_ran = $records.Count
  output = $outPath
  last = if ($records.Count) { $records[$records.Count - 1] } else { $null }
}
$result | ConvertTo-Json -Depth 8
