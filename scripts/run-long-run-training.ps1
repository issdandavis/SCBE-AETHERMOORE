param(
    [int]$Hours = 8,
    [string[]]$Providers = @(),
    [switch]$Execute,
    [switch]$AllowPending,
    [string]$Plan = "training/long_run_multicloud_training_plan.json",
    [string]$RunRoot = "training/runs"
)

$ErrorActionPreference = "Stop"

$argsList = @(
  "--plan", $Plan,
  "--hours", $Hours.ToString(),
  "--run-root", $RunRoot
)

if ($Providers.Count -gt 0) {
  $argsList += @("--providers", ($Providers -join ","))
}

if ($AllowPending.IsPresent) {
  $argsList += "--allow-pending"
}

if ($Execute.IsPresent) {
  $argsList += "--execute"
} else {
  $argsList += "--dry-run"
}

& python (Join-Path $PSScriptRoot "long_run_training_bootstrap.py") @argsList
