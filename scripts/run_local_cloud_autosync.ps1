[CmdletBinding()]
param(
    [string]$Config = "training/local_cloud_sync.json",
    [string]$RunRoot = "training/runs/local_cloud_sync",
    [string]$StateFile = "training/ingest/local_cloud_sync_state.json",
    [string]$LatestPointer = "training/ingest/latest_local_cloud_sync.txt",
    [switch]$Once,
    [int]$IntervalSeconds = 0,
    [switch]$Force,
    [switch]$NoUpload,
    [string]$ShipTargets = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$cmd = @(
    "python",
    "scripts/local_cloud_autosync.py",
    "--config", $Config,
    "--run-root", $RunRoot,
    "--state-file", $StateFile,
    "--latest-pointer", $LatestPointer
)

if ($Once) {
    $cmd += "--once"
}
if ($IntervalSeconds -gt 0) {
    $cmd += @("--interval-seconds", "$IntervalSeconds")
}
if ($Force) {
    $cmd += "--force"
}
if ($NoUpload) {
    $cmd += "--no-upload"
}
if ($ShipTargets) {
    $cmd += @("--ship-targets", $ShipTargets)
}

Write-Host ("$ " + ($cmd -join " "))
& $cmd[0] $cmd[1..($cmd.Count - 1)]
exit $LASTEXITCODE
