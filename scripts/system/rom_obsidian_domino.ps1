param(
  [Parameter(Mandatory = $true)]
  [string]$RomPath,
  [string]$VaultPath = $env:OBSIDIAN_VAULT_PATH,
  [bool]$InitHub = $true,
  [switch]$SyncNotion = $false,
  [string[]]$NotionConfigKey = @(),
  [int]$Steps = 8000,
  [int]$SampleEvery = 8,
  [int]$OcrEvery = 20,
  [int]$MaxPairs = 600,
  [bool]$SmartAgent = $true,
  [string]$Game = "pokemon_crystal",
  [switch]$CaptureGif = $false,
  [string]$GifPath = "",
  [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
  param(
    [string]$Name,
    [string[]]$Cmd
  )
  Write-Host ""
  Write-Host "==> $Name"
  Write-Host ("$($Cmd -join ' ')")
  & $Cmd[0] $Cmd[1..($Cmd.Length - 1)]
  if ($LASTEXITCODE -ne 0) {
    throw "Step failed ($Name) with exit code $LASTEXITCODE"
  }
}

function Append-Event {
  param(
    [string]$Path,
    [hashtable]$Event
  )
  New-Item -ItemType Directory -Force -Path (Split-Path $Path) | Out-Null
  ($Event | ConvertTo-Json -Compress) | Add-Content -Path $Path -Encoding UTF8
}

if (-not (Test-Path $RomPath)) {
  throw "ROM path not found: $RomPath"
}

if (-not $VaultPath) {
  throw "Vault path required. Set -VaultPath or OBSIDIAN_VAULT_PATH."
}

if (-not (Test-Path $VaultPath)) {
  throw "Vault path not found: $VaultPath"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$runStamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$eventsFile = "training/runs/rom_obsidian_domino/events.jsonl"

Append-Event -Path $eventsFile -Event @{
  event = "rom_obsidian_domino_started"
  timestamp = $timestamp
  rom_path = $RomPath
  vault_path = $VaultPath
  init_hub = [bool]$InitHub
  sync_notion = [bool]$SyncNotion
  dry_run = [bool]$DryRun
}

try {
  $romCmd = @(
    "python",
    "demo/rom_emulator_bridge.py",
    "--rom", $RomPath,
    "--steps", "$Steps",
    "--sample-every", "$SampleEvery",
    "--ocr-every", "$OcrEvery",
    "--max-pairs", "$MaxPairs",
    "--i-own-this-rom"
  )

  if ($SmartAgent) {
    $romCmd += "--smart-agent"
    if ($Game) {
      $romCmd += @("--game", $Game)
    }
  }

  if ($CaptureGif) {
    if (-not $GifPath) {
      $GifPath = "training/runs/rom_obsidian_domino/$runStamp/rom_preview.gif"
    }
    $gifDir = Split-Path $GifPath
    if ($gifDir) {
      New-Item -ItemType Directory -Force -Path $gifDir | Out-Null
    }
    $romCmd += @("--gif", $GifPath)
  }

  if ($DryRun) {
    Write-Host ""
    Write-Host "==> Stage 1: ROM bridge (planned)"
    Write-Host ("$($romCmd -join ' ')")
  } else {
    Invoke-Step -Name "Stage 1: ROM bridge" -Cmd $romCmd
  }

  $dominoCmd = @(
    ".\scripts\system\obsidian_multi_ai_domino.ps1",
    "-VaultPath", $VaultPath
  )

  if ($InitHub) { $dominoCmd += "-InitHub" }
  if ($SyncNotion) { $dominoCmd += "-SyncNotion" }
  foreach ($key in $NotionConfigKey) {
    if ($key) {
      $dominoCmd += @("-NotionConfigKey", $key)
    }
  }
  if ($DryRun) { $dominoCmd += "-DryRun" }

  Invoke-Step -Name "Stage 2: Obsidian domino sync" -Cmd $dominoCmd

  $latestJsonl = Get-ChildItem "training-data/rom_sessions" -Filter *.jsonl -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  $romHubDir = Join-Path $VaultPath "SCBE-Hub\04-Runs\rom-sessions\$runStamp"
  New-Item -ItemType Directory -Force -Path $romHubDir | Out-Null

  $copiedJsonl = ""
  if ($latestJsonl) {
    Copy-Item $latestJsonl.FullName -Destination (Join-Path $romHubDir $latestJsonl.Name) -Force
    $copiedJsonl = Join-Path $romHubDir $latestJsonl.Name
  }

  $copiedGif = ""
  if ($CaptureGif -and $GifPath -and (Test-Path $GifPath)) {
    $gifName = Split-Path $GifPath -Leaf
    Copy-Item $GifPath -Destination (Join-Path $romHubDir $gifName) -Force
    $copiedGif = Join-Path $romHubDir $gifName
  }

  $summaryPath = Join-Path $romHubDir "RUN_SUMMARY.md"
  @"
# ROM Session Summary

- timestamp_utc: $timestamp
- rom_path: $RomPath
- latest_jsonl: $copiedJsonl
- gif: $copiedGif
- vault_path: $VaultPath
- sync_notion: $([bool]$SyncNotion)
- init_hub: $([bool]$InitHub)
"@ | Set-Content -Path $summaryPath -Encoding UTF8

  Append-Event -Path $eventsFile -Event @{
    event = "rom_obsidian_domino_completed"
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    rom_path = $RomPath
    latest_jsonl = $copiedJsonl
    copied_gif = $copiedGif
    run_summary = $summaryPath
    vault_path = $VaultPath
  }

  Write-Host ""
  Write-Host "ROM -> Obsidian domino completed."
  Write-Host "Events: $eventsFile"
  if ($copiedJsonl) { Write-Host "JSONL copied: $copiedJsonl" }
  if ($copiedGif) { Write-Host "GIF copied: $copiedGif" }
  Write-Host "Run summary: $summaryPath"
}
catch {
  Append-Event -Path $eventsFile -Event @{
    event = "rom_obsidian_domino_failed"
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    rom_path = $RomPath
    vault_path = $VaultPath
    error = $_.Exception.Message
  }
  throw
}

