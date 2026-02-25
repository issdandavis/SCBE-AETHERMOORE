param(
  [string]$VaultPath = $env:OBSIDIAN_VAULT_PATH,
  [switch]$InitHub = $false,
  [switch]$SyncNotion = $false,
  [string[]]$NotionConfigKey = @(),
  [string]$HfDatasetRepo = "",
  [switch]$PushGit = $false,
  [switch]$SkipDropbox = $false,
  [string]$DropboxRemoteDir = "/SCBE/backups",
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

if (-not $VaultPath) {
  throw "Vault path required. Set -VaultPath or OBSIDIAN_VAULT_PATH."
}

if (-not (Test-Path $VaultPath)) {
  throw "Vault path not found: $VaultPath"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$eventsFile = "training/runs/multi_ai_sync/domino_events.jsonl"
New-Item -ItemType Directory -Force -Path (Split-Path $eventsFile) | Out-Null

$eventStart = @{
  event = "domino_started"
  timestamp = $timestamp
  vault_path = $VaultPath
  init_hub = [bool]$InitHub
  sync_notion = [bool]$SyncNotion
  push_git = [bool]$PushGit
  skip_dropbox = [bool]$SkipDropbox
  dry_run = [bool]$DryRun
}
($eventStart | ConvertTo-Json -Compress) | Add-Content -Path $eventsFile -Encoding UTF8

try {
  # Stage 1: Multi-AI dataset/content sync.
  $syncCmd = @("python", "scripts/run_multi_ai_content_sync.py")
  if ($SyncNotion) { $syncCmd += "--sync-notion" }
  foreach ($key in $NotionConfigKey) {
    if ($key) {
      $syncCmd += @("--notion-config-key", $key)
    }
  }
  if ($HfDatasetRepo) { $syncCmd += @("--hf-dataset-repo", $HfDatasetRepo) }
  if ($DryRun) {
    Write-Host ""
    Write-Host "==> Stage 1: multi-ai content sync (planned)"
    Write-Host ("$($syncCmd -join ' ')")
  }
  else {
    Invoke-Step -Name "Stage 1: multi-ai content sync" -Cmd $syncCmd
  }

  # Stage 2: Hub sync into Obsidian + optional Git/Dropbox + webhook events.
  $hubCmd = @(
    "python",
    "scripts/system/system_hub_sync.py",
    "--vault-path",
    $VaultPath,
    "--dropbox-remote-dir",
    $DropboxRemoteDir
  )
  if ($InitHub) { $hubCmd += "--init-obsidian-hub" }
  if ($PushGit) { $hubCmd += "--push" }
  if ($SkipDropbox) { $hubCmd += "--skip-dropbox" }
  if ($DryRun) { $hubCmd += "--dry-run" }
  Invoke-Step -Name "Stage 2: system hub sync" -Cmd $hubCmd

  $eventDone = @{
    event = "domino_completed"
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    vault_path = $VaultPath
    latest_pointer = "training/ingest/latest_multi_ai_sync.txt"
    map_room = "docs/map-room/session_handoff_latest.md"
  }
  ($eventDone | ConvertTo-Json -Compress) | Add-Content -Path $eventsFile -Encoding UTF8

  Write-Host ""
  Write-Host "Domino workflow completed."
  Write-Host "Events: $eventsFile"
  Write-Host "Latest pointer: training/ingest/latest_multi_ai_sync.txt"
}
catch {
  $eventFail = @{
    event = "domino_failed"
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    vault_path = $VaultPath
    error = $_.Exception.Message
  }
  ($eventFail | ConvertTo-Json -Compress) | Add-Content -Path $eventsFile -Encoding UTF8
  throw
}
