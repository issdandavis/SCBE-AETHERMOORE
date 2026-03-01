$ErrorActionPreference = "Stop"

$projectRoot = "C:\Users\issda\SCBE-AETHERMOORE"
$watchdogScript = Join-Path $projectRoot "scripts\system\watchdog_agent_stack.ps1"

if (-not (Test-Path $watchdogScript)) {
    throw "Missing watchdog script: $watchdogScript"
}

& $watchdogScript `
    -ProjectRoot $projectRoot `
    -N8nUserFolder "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local_iso" `
    -BridgePort 8002 `
    -BrowserPort 8012 `
    -N8nPort 5680 `
    -N8nTaskBrokerPort 5681 `
    -StartOpenClaw `
    -OpenClawGatewayPort 18789 `
    -OpenClawBridgePort 18790
