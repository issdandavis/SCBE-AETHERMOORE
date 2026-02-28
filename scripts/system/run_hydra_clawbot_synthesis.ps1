param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$N8nUrl = "http://127.0.0.1:5680",
    [string]$ZapierConnectorName = "zapier-main-hook",
    [string]$TelegramConnectorName = "telegram-ops-generic",
    [string]$NotionConnectorName = "notion-research-sync",
    [string]$SwarmConnectorName = "n8n-swarm-intake",
    [switch]$SkipZapier,
    [switch]$SkipTelegram,
    [switch]$SkipNotion,
    [switch]$SkipSwarm
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$goalScript = Join-Path $RepoRoot "scripts\system\run_connector_goal.ps1"
if (-not (Test-Path $goalScript)) {
    throw "Missing run_connector_goal.ps1 at $goalScript"
}

$outDir = Join-Path $RepoRoot "artifacts\system_smoke"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$run = [ordered]@{
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    base_url = $BaseUrl
    n8n_url = $N8nUrl
    phases = [ordered]@{
        SENSE = @()
        PLAN = @()
        EXECUTE = @()
        PUBLISH = @()
    }
}

function Invoke-Goal {
    param(
        [string]$Goal,
        [string]$ConnectorName
    )
    $raw = & $goalScript -Goal $Goal -ConnectorName $ConnectorName -BaseUrl $BaseUrl
    return $raw | ConvertFrom-Json
}

# SENSE
if (-not $SkipNotion) {
    $run.phases.SENSE += Invoke-Goal -Goal "sense context from notion and docs" -ConnectorName $NotionConnectorName
}
if (-not $SkipSwarm) {
    $run.phases.SENSE += Invoke-Goal -Goal "sense context from n8n swarm intake" -ConnectorName $SwarmConnectorName
}

# PLAN
if (-not $SkipSwarm) {
    $run.phases.PLAN += Invoke-Goal -Goal "plan governed execution route for openclaw-style workload" -ConnectorName $SwarmConnectorName
}

# EXECUTE
if (-not $SkipTelegram) {
    $run.phases.EXECUTE += Invoke-Goal -Goal "execute telegram automation route" -ConnectorName $TelegramConnectorName
}

# PUBLISH
if (-not $SkipZapier) {
    $run.phases.PUBLISH += Invoke-Goal -Goal "publish automation event to zapier sink" -ConnectorName $ZapierConnectorName
}

$outFile = Join-Path $outDir "hydra_clawbot_synthesis_run.json"
$run | ConvertTo-Json -Depth 8 | Set-Content -Path $outFile
$run | ConvertTo-Json -Depth 8
