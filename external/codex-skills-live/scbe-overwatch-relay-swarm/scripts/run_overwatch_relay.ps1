param(
    [Parameter(Mandatory = $true)][string]$Task,
    [ValidateSet("money", "research")][string]$Mode = "money",
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$argsList = @("scripts/system/overwatch_baton.py", "--task", $Task, "--mode", $Mode, "--repo-root", $RepoRoot)
if ($DryRun) {
    $argsList += "--dry-run"
}

python @argsList
