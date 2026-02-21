param(
    [string]$Config = "training/cloud_kernel_pipeline.json",
    [string]$RunRoot = "training/runs/cloud_kernel_sync",
    [string[]]$Glob = @(),
    [switch]$SyncNotion,
    [string[]]$NotionConfigKey = @(),
    [string]$ShipTargets = "hf,github",
    [switch]$NoUpload,
    [int]$KeepRuns = 30,
    [switch]$AllowQuarantine,
    [switch]$ShipOnQuarantine
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$cmd = @(
    "python", "scripts/cloud_kernel_data_pipeline.py",
    "--config", $Config,
    "--run-root", $RunRoot,
    "--ship-targets", $ShipTargets,
    "--keep-runs", "$KeepRuns"
)

if ($SyncNotion) {
    $cmd += "--sync-notion"
}
foreach ($key in $NotionConfigKey) {
    $cmd += @("--notion-config-key", $key)
}
foreach ($pattern in $Glob) {
    $cmd += @("--glob", $pattern)
}
if ($NoUpload) {
    $cmd += "--no-upload"
}
if ($AllowQuarantine) {
    $cmd += "--allow-quarantine"
}
if ($ShipOnQuarantine) {
    $cmd += "--ship-on-quarantine"
}

& $cmd[0] $cmd[1..($cmd.Count - 1)]
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
