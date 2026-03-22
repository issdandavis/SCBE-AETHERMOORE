param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$Store = "aethermore-code.myshopify.com",
    [switch]$PublishLive = $false,
    [switch]$SkipConnectorCheck = $false
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $RepoRoot "scripts\system\run_profit_autopilot.ps1"
if (-not (Test-Path $runner)) {
    throw "Missing pipeline runner: $runner"
}

$argsList = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $runner,
    "-RepoRoot", $RepoRoot,
    "-Store", $Store
)
if ($PublishLive) {
    $argsList += "-PublishLive"
}
if ($SkipConnectorCheck) {
    $argsList += "-SkipConnectorCheck"
}

pwsh @argsList
