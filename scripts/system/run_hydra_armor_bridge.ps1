param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$N8nUrl = "http://127.0.0.1:5680",
    [string]$BridgeUrl = "http://127.0.0.1:8002",
    [string]$BrowserUrl = "http://127.0.0.1:8012",
    [string]$NotionConnectorName = "notion-research-sync",
    [string]$GithubConnectorName = "github-actions-fleet",
    [string]$SwarmWebhookPath = "scbe-notion-github-swarm",
    [string[]]$NotionUrls = @(
        "https://aethermoorgames.notion.site/SCBE-AETHERMOORE-Hub-300f96de82e580d09a66cdd048e5cab5",
        "https://aethermoorgames.notion.site/GeoSeed-Network-6-Seed-Neural-Architecture-Design-313f96de82e581e1ad61d3d711140391"
    ),
    [string[]]$GithubUrls = @(
        "https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/docs/hydra",
        "https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/workflows/n8n"
    ),
    [switch]$SkipConnectorGoals,
    [switch]$SkipSwarmTrigger
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$outDir = Join-Path $RepoRoot "artifacts\system_smoke"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$result = [ordered]@{
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    repo_root = $RepoRoot
    base_url = $BaseUrl
    n8n_url = $N8nUrl
    bridge_url = $BridgeUrl
    browser_url = $BrowserUrl
    connectors = @{}
    swarm_trigger = $null
    smoke = $null
}

$goalScript = Join-Path $RepoRoot "scripts\system\run_connector_goal.ps1"
if (-not (Test-Path $goalScript)) {
    throw "Missing script: $goalScript"
}

if (-not $SkipConnectorGoals) {
    $notionGoal = & $goalScript -Goal "hydrate hydra armor from notion context" -ConnectorName $NotionConnectorName -BaseUrl $BaseUrl | ConvertFrom-Json
    $githubGoal = & $goalScript -Goal "hydrate hydra armor from github context" -ConnectorName $GithubConnectorName -BaseUrl $BaseUrl | ConvertFrom-Json

    $result.connectors[$NotionConnectorName] = $notionGoal
    $result.connectors[$GithubConnectorName] = $githubGoal
}

if (-not $SkipSwarmTrigger) {
    $payload = @{
        run_id = "hydra-armor-$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())"
        query = "Hydra Armor synthesis from Notion and GitHub"
        max_sources = 5
        notion_urls = $NotionUrls
        github_urls = $GithubUrls
    } | ConvertTo-Json -Depth 6

    $webhookUrl = "{0}/webhook/{1}" -f $N8nUrl.TrimEnd("/"), $SwarmWebhookPath
    $swarmResponse = Invoke-RestMethod -Method Post -Uri $webhookUrl -ContentType "application/json" -Body $payload
    $result.swarm_trigger = @{
        webhook = $webhookUrl
        response = $swarmResponse
    }
}

$smokeReport = Join-Path $outDir "hydra_armor_smoke.json"
python scripts/system/full_system_smoke.py --bridge-url $BridgeUrl --browser-url $BrowserUrl --n8n-url $N8nUrl --probe-webhook --output $smokeReport
if ($LASTEXITCODE -ne 0) {
    throw "full_system_smoke.py failed while running Hydra Armor bridge."
}
$result.smoke = @{
    report = $smokeReport
}

$outFile = Join-Path $outDir "hydra_armor_bridge_run.json"
$result | ConvertTo-Json -Depth 8 | Set-Content -Path $outFile
$result | ConvertTo-Json -Depth 8

