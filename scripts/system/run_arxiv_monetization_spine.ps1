param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string[]]$Query = @(
        "ai agent workflow automation",
        "llm evaluation safety governance",
        "browser automation multi agent systems"
    ),
    [int]$MaxPerQuery = 5,
    [int]$TopLeads = 10,
    [string]$Category = "",
    [ValidateSet("playwriter", "playwright")]
    [string]$Engine = "playwriter",
    [switch]$NoRouteN8n,
    [switch]$NoRouteZapier,
    [switch]$DryRunRouting,
    [switch]$DispatchMonetizationSwarm,
    [switch]$CapturePlaywriterEvidence,
    [string]$PlaywriterSession = "1",
    [string]$Codename = "RevenueSpine-Arxiv"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$scriptPath = Join-Path $RepoRoot "scripts\system\arxiv_monetization_spine.py"
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$argsList = @(
    $scriptPath,
    "--max-per-query", "$MaxPerQuery",
    "--top-leads", "$TopLeads",
    "--engine", $Engine,
    "--codename", $Codename
)

if (-not [string]::IsNullOrWhiteSpace($Category)) {
    $argsList += @("--category", $Category)
}

foreach ($q in $Query) {
    if (-not [string]::IsNullOrWhiteSpace($q)) {
        $argsList += @("--query", $q)
    }
}

if ($NoRouteN8n) {
    $argsList += "--no-route-n8n"
}
if ($NoRouteZapier) {
    $argsList += "--no-route-zapier"
}
if ($DryRunRouting) {
    $argsList += "--dry-run-routing"
}
if ($DispatchMonetizationSwarm) {
    $argsList += "--dispatch-monetization-swarm"
}
if ($CapturePlaywriterEvidence) {
    $argsList += @("--capture-playwriter-evidence", "--playwriter-session", $PlaywriterSession)
}

python @argsList
