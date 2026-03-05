param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$Store = "aethermore-code.myshopify.com",
    [switch]$RunBothSideTest = $true,
    [switch]$PublishLive = $false,
    [switch]$EmitCrosstalk = $true
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$scriptPath = Join-Path $RepoRoot "scripts\system\shopify_store_launch_pack.py"
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$argsList = @(
    $scriptPath,
    "--store", $Store
)

if ($RunBothSideTest) {
    $argsList += "--run-both-side-test"
}
if ($PublishLive) {
    $argsList += "--publish-live"
}
if ($EmitCrosstalk) {
    $argsList += "--emit-crosstalk"
}

python @argsList

