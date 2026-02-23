param(
    [string]$OrdersFile = "examples/polly_clay_orders.gumroad.sample.json",
    [string]$ApiKey = "",
    [string]$RiskContract = "MID",
    [string]$EndpointUrl = "",
    [int]$Clays = 4,
    [int]$Port = 8014,
    [switch]$Continuous,
    [int]$PollSec = 30,
    [switch]$OpenHitlBrowser,
    [switch]$StartLocalService = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    if ($env:SCBE_API_KEY) {
        $ApiKey = $env:SCBE_API_KEY.Trim()
    }
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = "polly-clay-demo-key"
}

$args = @(
    "scripts/polly_clay_squad.py",
    "--orders-file", $OrdersFile,
    "--api-key", $ApiKey,
    "--risk-contract", $RiskContract,
    "--clays", "$Clays",
    "--output-json", "artifacts/polly_clay/summary_latest.json",
    "--hitl-dir", "artifacts/polly_clay/hitl"
)

if (-not [string]::IsNullOrWhiteSpace($EndpointUrl)) {
    $args += @("--url", $EndpointUrl)
}

if ($StartLocalService) {
    $args += @("--start-local-service", "--service-host", "127.0.0.1", "--service-port", "$Port")
}

if ($Continuous) {
    $args += @("--continuous", "--poll-sec", "$PollSec")
}

if ($OpenHitlBrowser) {
    $args += "--open-hitl-browser"
}

Write-Host "Running Polly+Clay squad..." -ForegroundColor Cyan
Write-Host ("Orders: {0}" -f $OrdersFile) -ForegroundColor Cyan
Write-Host ("Clays:  {0}" -f $Clays) -ForegroundColor Cyan
Write-Host ("Tier:   {0}" -f $RiskContract) -ForegroundColor Cyan
if ($StartLocalService) {
    Write-Host ("Local service port: {0}" -f $Port) -ForegroundColor Cyan
}
python @args
