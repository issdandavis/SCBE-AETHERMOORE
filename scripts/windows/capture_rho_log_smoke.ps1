#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot: synthetic rho JSONL + analyzer table (local Windows smoke).

.DESCRIPTION
  Default: truncates the default log, runs generate_sample_rho_log.py, then analyze_rho_log.py.
  -AnalyzeOnly: run the analyzer only (use after live traffic with SCBE_RHO_LOG=1).
  -NoTruncate: append synthetic samples instead of deleting the log first (advanced).

  Task Scheduler (optional):
    Program: powershell.exe
    Arguments: -NoProfile -ExecutionPolicy Bypass -File "C:\path\to\SCBE-AETHERMOORE\scripts\windows\capture_rho_log_smoke.ps1"
  Nightly readout (analyze existing log only):
    ... capture_rho_log_smoke.ps1 -AnalyzeOnly -Hint

.PARAMETER RepoRoot
  Absolute path to repo root. Default: grandparent of this script's directory.

.PARAMETER Iterations
  Passed through to generate_sample_rho_log.py

.PARAMETER Json
  If set, analyzer prints JSON instead of a table.

.PARAMETER AnalyzeOnly
  Skip generator; only run analyze_rho_log.py on the default log path.

.PARAMETER NoTruncate
  When generating, do not delete the log file first (append synthetic records).

.PARAMETER Hint
  Pass --hint to the analyzer (verdict: static baseline vs dynamic radii experiment).
#>
param(
    [string] $RepoRoot = "",
    [int] $Iterations = 128,
    [switch] $Json,
    [switch] $AnalyzeOnly,
    [switch] $NoTruncate,
    [switch] $Hint
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
Set-Location $RepoRoot

$env:PYTHONPATH = $RepoRoot

$logPath = Join-Path $RepoRoot "artifacts\rho_logging\composite_wall_rho.jsonl"
New-Item -ItemType Directory -Force -Path (Split-Path $logPath) | Out-Null

if (-not $AnalyzeOnly) {
    $genArgs = @(
        (Join-Path $RepoRoot "scripts\rho_logging\generate_sample_rho_log.py"),
        "--iterations", $Iterations,
        "--path", $logPath
    )
    if (-not $NoTruncate) {
        $genArgs += "--truncate"
    }
    & python @genArgs
}

$analyzeArgs = @((Join-Path $RepoRoot "scripts\analyze_rho_log.py"), "--path", $logPath)
if ($Json) {
    $analyzeArgs += "--json"
}
if ($Hint) {
    $analyzeArgs += "--hint"
}
& python @analyzeArgs
