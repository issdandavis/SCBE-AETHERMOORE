$ErrorActionPreference = "Stop"

$projectRoot = "C:\Users\issda\SCBE-AETHERMOORE"
$startScript = Join-Path $projectRoot "workflows\n8n\start_n8n_local.ps1"

if (-not (Test-Path $startScript)) {
    throw "Missing start script: $startScript"
}

& $startScript `
    -ProjectRoot $projectRoot `
    -N8nUserFolder "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso" `
    -BridgePort 8002 `
    -BrowserPort 8012 `
    -N8nPort 5680 `
    -N8nTaskBrokerPort 5681 `
    -StartBrowserAgent

