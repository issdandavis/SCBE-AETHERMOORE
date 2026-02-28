param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$jobRoot = Join-Path $RepoRoot "artifacts\background_jobs\gaming_domains"
$latestPath = Join-Path $jobRoot "latest.json"

if (-not (Test-Path $latestPath)) {
    throw "No background gaming domain job metadata found at $latestPath"
}

$latest = Get-Content -Raw $latestPath | ConvertFrom-Json
$running = $false
try {
    $p = Get-Process -Id ([int]$latest.pid) -ErrorAction Stop
    if ($p) { $running = $true }
} catch {
    $running = $false
}

$runRoot = Join-Path $RepoRoot "training\runs\web_research"
$latestRunDir = Get-ChildItem $runRoot -Directory -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

$summaryPath = $null
if ($latestRunDir) {
    $summaryPath = Join-Path $latestRunDir.FullName "summary.json"
}

$tail = @()
if ($latest.stdout_log -and (Test-Path $latest.stdout_log)) {
    $tail = Get-Content $latest.stdout_log -Tail 20
}

[ordered]@{
    pid = $latest.pid
    running = $running
    started_utc = $latest.started_utc
    stdout_log = $latest.stdout_log
    stderr_log = $latest.stderr_log
    latest_run_dir = if ($latestRunDir) { $latestRunDir.FullName } else { "" }
    latest_summary_path = if ($summaryPath) { $summaryPath } else { "" }
    stdout_tail = $tail
} | ConvertTo-Json -Depth 8
