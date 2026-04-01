param(
    [string]$InstallationId,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$tokenScript = Join-Path $scriptRoot "latticegate_token.py"

if (-not (Test-Path $tokenScript)) {
    throw "Missing token helper: $tokenScript"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python is required to mint a GitHub App token."
}

$argsList = @($tokenScript)
if ($InstallationId) {
    $argsList += @("--installation-id", $InstallationId)
}
if ($Json) {
    $argsList += "--json"
    & $python.Source @argsList
    exit $LASTEXITCODE
}

$token = (& $python.Source @argsList).Trim()
if (-not $token) {
    throw "Token helper returned an empty token."
}

$env:GH_TOKEN = $token
$env:GITHUB_TOKEN = $token

Write-Host "GH_TOKEN exported for this shell."
Write-Host "Examples:"
Write-Host "  gh api user"
Write-Host "  gh api repos/issdandavis/SCBE-AETHERMOORE/pulls"
Write-Host "  gh api repos/issdandavis/SCBE-AETHERMOORE/check-runs"
