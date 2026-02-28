param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$latestPath = Join-Path $RepoRoot "artifacts\background_jobs\gaming_domains\latest.json"
if (-not (Test-Path $latestPath)) {
    throw "No background gaming domain job metadata found at $latestPath"
}

$latest = Get-Content -Raw $latestPath | ConvertFrom-Json
$pid = [int]$latest.pid

try {
    Stop-Process -Id $pid -Force -ErrorAction Stop
    [ordered]@{
        status = "stopped"
        pid = $pid
        stopped_utc = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json -Depth 4
} catch {
    [ordered]@{
        status = "not_running"
        pid = $pid
        detail = $_.Exception.Message
    } | ConvertTo-Json -Depth 4
}
