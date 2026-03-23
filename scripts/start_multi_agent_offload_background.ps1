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
    [switch]$NoProcess,
    [switch]$DeleteSource,
    [switch]$Reprocess,
    [string[]]$SourceRoot = @(),
    [string]$LogPath = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

if (-not $LogPath) {
    $stamp = Get-Date -Format "yyyyMMddTHHmmssZ"
    $LogPath = "training/runs/multi_agent_offload/background-$stamp.log"
}

$resolvedLog = Join-Path (Get-Location) $LogPath
$resolvedErr = "$resolvedLog.err"
$logDir = Split-Path -Parent $resolvedLog
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$argsList = @(
    "scripts/multi_agent_offload.py",
    "--config", $Config,
    "--state-path", $StatePath,
    "--run-root", $RunRoot,
    "--latest-pointer", $LatestPointer
)

if ($Targets) {
    $argsList += @("--targets", $Targets)
}
if ($BatchSize -gt 0) {
    $argsList += @("--batch-size", "$BatchSize")
}
if ($BatchDelaySeconds -gt 0) {
    $argsList += @("--batch-delay-seconds", "$BatchDelaySeconds")
}
if ($MaxFiles -gt 0) {
    $argsList += @("--max-files", "$MaxFiles")
}
if ($NoProcess) {
    $argsList += "--no-process"
}
if ($DeleteSource) {
    $argsList += "--delete-source"
}
if ($Reprocess) {
    $argsList += "--reprocess"
}
foreach ($root in $SourceRoot) {
    if ($root) {
        $argsList += @("--source-root", $root)
    }
}

$proc = Start-Process -FilePath "python" -ArgumentList $argsList -WorkingDirectory (Get-Location) -RedirectStandardOutput $resolvedLog -RedirectStandardError $resolvedErr -PassThru
Write-Host "Started multi-agent offload in background."
Write-Host "PID: $($proc.Id)"
Write-Host "Log: $resolvedLog"
Write-Host "Err: $resolvedErr"
