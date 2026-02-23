param(
    [string]$RunRoot = "training/runs/multi_ai_sync",
    [string[]]$Glob = @(),
    [switch]$SyncNotion,
    [string[]]$NotionConfigKey = @(),
    [switch]$SkipDocManifest,
    [string]$Attest = "claude,gpt,sonar",
    [string]$HfDatasetRepo = "",
    [switch]$NoArchive
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$cmd = @("python", "scripts/run_multi_ai_content_sync.py", "--run-root", $RunRoot, "--attest", $Attest)

if ($SyncNotion) {
    $cmd += "--sync-notion"
}
foreach ($key in $NotionConfigKey) {
    $cmd += @("--notion-config-key", $key)
}
if ($SkipDocManifest) {
    $cmd += "--skip-doc-manifest"
}
foreach ($pattern in $Glob) {
    $cmd += @("--glob", $pattern)
}
if ($HfDatasetRepo) {
    $cmd += @("--hf-dataset-repo", $HfDatasetRepo)
}
if ($NoArchive) {
    $cmd += "--no-archive"
}

& $cmd[0] $cmd[1..($cmd.Count - 1)]

