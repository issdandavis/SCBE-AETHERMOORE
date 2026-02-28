param(
    [string]$BridgeUrl = "http://127.0.0.1:8001",
    [string]$BrowserUrl = "http://127.0.0.1:8011",
    [string]$N8nUrl = "http://127.0.0.1:5678",
    [string]$ApiKey = "",
    [double]$StartupWaitSec = 45,
    [double]$TimeoutSec = 20,
    [double]$PollSeconds = 15,
    [switch]$RequireWebhook,
    [switch]$ProbeWebhook,
    [switch]$BrowseReal,
    [switch]$SkipBrowser,
    [switch]$SkipN8n,
    [switch]$SkipGovernance,
    [switch]$SkipBuffer,
    [switch]$SkipBrowse,
    [switch]$SkipAgentTask,
    [string]$WebhookPath = "scbe-notion-github-swarm",
    [string]$Output = "artifacts/system_smoke/full_system_smoke_report.json",
    [switch]$PrintJson
)

$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "full_system_smoke.py"
if (-not (Test-Path $scriptPath)) {
    throw "Smoke script not found: $scriptPath"
}

$argsList = @(
    $scriptPath,
    "--bridge-url", $BridgeUrl,
    "--browser-url", $BrowserUrl,
    "--n8n-url", $N8nUrl,
    "--startup-wait-sec", "$StartupWaitSec",
    "--timeout-sec", "$TimeoutSec",
    "--poll-seconds", "$PollSeconds",
    "--webhook-path", $WebhookPath,
    "--output", $Output
)

if ($ApiKey) { $argsList += @("--api-key", $ApiKey) }
if ($RequireWebhook) { $argsList += "--require-webhook" }
if ($ProbeWebhook) { $argsList += "--probe-webhook" }
if ($BrowseReal) { $argsList += "--browse-real" }
if ($SkipBrowser) { $argsList += "--skip-browser" }
if ($SkipN8n) { $argsList += "--skip-n8n" }
if ($SkipGovernance) { $argsList += "--skip-governance" }
if ($SkipBuffer) { $argsList += "--skip-buffer" }
if ($SkipBrowse) { $argsList += "--skip-browse" }
if ($SkipAgentTask) { $argsList += "--skip-agent-task" }
if ($PrintJson) { $argsList += "--print-json" }

Write-Host "[SCBE] Running full-system smoke test..."
python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Full-system smoke test failed with exit code $LASTEXITCODE."
}

Write-Host "[SCBE] Full-system smoke test passed."
