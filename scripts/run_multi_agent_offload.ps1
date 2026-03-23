[CmdletBinding()]
param(
    [string]$Config = "scripts/multi_agent_offload.json",
    [string]$StatePath = "training/ingest/multi_agent_offload_state.json",
    [string]$RunRoot = "training/runs/multi_agent_offload",
    [string]$LatestPointer = "training/ingest/latest_multi_agent_offload.txt",
    [string]$Targets = "",
    [int]$BatchSize = 0,
    [double]$BatchDelaySeconds = 0,
    [int]$MaxFiles = 0,
    [switch]$DryRun,
    [switch]$NoProcess,
    [switch]$DeleteSource,
    [switch]$Reprocess,
    [string[]]$SourceRoot = @()
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$cmd = @(
    "python",
    "scripts/multi_agent_offload.py",
    "--config", $Config,
    "--state-path", $StatePath,
    "--run-root", $RunRoot,
    "--latest-pointer", $LatestPointer
)

if ($Targets) {
    $cmd += @("--targets", $Targets)
}
if ($BatchSize -gt 0) {
    $cmd += @("--batch-size", "$BatchSize")
}
if ($BatchDelaySeconds -gt 0) {
    $cmd += @("--batch-delay-seconds", "$BatchDelaySeconds")
}
if ($MaxFiles -gt 0) {
    $cmd += @("--max-files", "$MaxFiles")
}
if ($DryRun) {
    $cmd += "--dry-run"
}
if ($NoProcess) {
    $cmd += "--no-process"
}
if ($DeleteSource) {
    $cmd += "--delete-source"
}
if ($Reprocess) {
    $cmd += "--reprocess"
}
foreach ($root in $SourceRoot) {
    if ($root) {
        $cmd += @("--source-root", $root)
    }
}

Write-Host ("$ " + ($cmd -join " "))
& $cmd[0] $cmd[1..($cmd.Count - 1)]
exit $LASTEXITCODE
