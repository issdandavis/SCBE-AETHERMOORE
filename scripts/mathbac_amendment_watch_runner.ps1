param(
  [string]$OpportunityId = "3b5f6dd94f45409b8b7995c83e4e7f94",
  [string]$Baseline = "",
  [string]$SnapshotDir = "",
  [string]$PaPdf = "",
  [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot   = Resolve-Path (Join-Path $PSScriptRoot "..")
$logDir     = Join-Path $repoRoot "artifacts\mathbac\amendment_watch_runner_log"
$reportDir  = Join-Path $repoRoot "artifacts\mathbac\amendment_watch"
$defaultSnapshotDir = Join-Path $repoRoot "artifacts\mathbac\snapshots"
$pyScript   = Join-Path $repoRoot "scripts\mathbac_amendment_watch.py"

New-Item -ItemType Directory -Path $logDir    -Force | Out-Null
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null

$utcStamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$logPath  = Join-Path $logDir ("amendment_watch_runner_" + $utcStamp + ".json")

function Write-Log($obj) {
  $json = ($obj | ConvertTo-Json -Depth 8)
  if ($null -eq $json) { $json = "{}" }
  [System.IO.File]::WriteAllText($logPath, [string]$json, (New-Object System.Text.UTF8Encoding($false)))
}

$record = [ordered]@{
  schema_version  = 1
  started_utc     = (Get-Date).ToUniversalTime().ToString("o")
  repo_root       = "$repoRoot"
  opportunity_id  = $OpportunityId
  mode            = $null
  python_exit     = $null
  runner_exit     = 0
  notes           = @()
  python_stdout   = $null
  python_stderr   = $null
  report_dir      = "$reportDir"
}

if (-not (Test-Path $pyScript)) {
  $record.notes += "missing_python_script: $pyScript"
  $record.runner_exit = 2
  $record.finished_utc = (Get-Date).ToUniversalTime().ToString("o")
  Write-Log $record
  exit 2
}

$apiKey = $env:SAM_GOV_API_KEY
if ([string]::IsNullOrWhiteSpace($apiKey)) { $apiKey = $env:DATA_GOV_API_KEY }

$pyArgs = @($pyScript, "--opportunity-id", $OpportunityId)
if ($Baseline) { $pyArgs += @("--baseline", $Baseline) }
if ($PaPdf)    { $pyArgs += @("--pa-pdf",   $PaPdf)    }
if ($Quiet)    { $pyArgs += "--quiet" }

if ([string]::IsNullOrWhiteSpace($apiKey)) {
  $effectiveSnapshotDir = $SnapshotDir
  if ([string]::IsNullOrWhiteSpace($effectiveSnapshotDir)) {
    $effectiveSnapshotDir = $defaultSnapshotDir
  }

  $snapshot = $null
  if (Test-Path $effectiveSnapshotDir) {
    $snapshot = Get-ChildItem -Path $effectiveSnapshotDir -Filter "*.json" -File -ErrorAction SilentlyContinue |
      Sort-Object -Property LastWriteTimeUtc -Descending |
      Select-Object -First 1
  }

  if ($null -eq $snapshot) {
    $record.mode = "no-source"
    $record.notes += "no_api_key_and_no_snapshot: skipped diff (kept exit 0 to avoid scheduler flap)"
    $record.notes += "snapshot_dir_searched: $effectiveSnapshotDir"
    $record.runner_exit = 0
    $record.finished_utc = (Get-Date).ToUniversalTime().ToString("o")
    Write-Log $record
    exit 0
  }

  $pyArgs += @("--snapshot", $snapshot.FullName)
  $record.mode = "snapshot"
  $record.notes += "snapshot_used: $($snapshot.FullName)"
} else {
  $record.mode = "live"
}

$stdoutPath = Join-Path $logDir ("amendment_watch_stdout_" + $utcStamp + ".txt")
$stderrPath = Join-Path $logDir ("amendment_watch_stderr_" + $utcStamp + ".txt")

try {
  $proc = Start-Process -FilePath "python" -ArgumentList $pyArgs `
    -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError  $stderrPath
  $record.python_exit = $proc.ExitCode
} catch {
  $record.notes += "python_invoke_error: $($_.Exception.Message)"
  $record.python_exit = -1
  $record.runner_exit = 2
  $record.finished_utc = (Get-Date).ToUniversalTime().ToString("o")
  Write-Log $record
  exit 2
}

if (Test-Path $stdoutPath) {
  $record.python_stdout = (Get-Content -Path $stdoutPath -Raw -ErrorAction SilentlyContinue)
}
if (Test-Path $stderrPath) {
  $record.python_stderr = (Get-Content -Path $stderrPath -Raw -ErrorAction SilentlyContinue)
}

# Pass through python's semantic exit code:
#   0 = no change (clean run)
#   1 = material change detected (review required)
#   2 = fetch failure (review credentials / network)
$record.runner_exit = $record.python_exit
$record.finished_utc = (Get-Date).ToUniversalTime().ToString("o")
Write-Log $record

exit $record.python_exit
