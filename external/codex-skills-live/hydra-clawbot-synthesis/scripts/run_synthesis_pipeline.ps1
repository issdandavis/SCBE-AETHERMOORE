param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$BridgeUrl = "http://127.0.0.1:8002",
    [string]$BrowserUrl = "http://127.0.0.1:8012",
    [string]$N8nUrl = "http://127.0.0.1:5680"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$outDir = Join-Path $RepoRoot "artifacts\page_evidence"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$smokeOut = Join-Path $RepoRoot "artifacts\system_smoke\synthesis_smoke.json"
python scripts/system/full_system_smoke.py --bridge-url $BridgeUrl --browser-url $BrowserUrl --n8n-url $N8nUrl --probe-webhook --output $smokeOut

$browseOut = Join-Path $outDir "synthesis_terminal_browse.json"
$browseScript = "C:\Users\issda\.codex\skills\hydra-node-terminal-browsing\scripts\hydra_terminal_browse.mjs"
if (Test-Path $browseScript) {
    node $browseScript --url "https://example.com" --out $browseOut
}

$bridgeScript = Join-Path $RepoRoot "scripts\system\run_hydra_armor_bridge.ps1"
if (Test-Path $bridgeScript) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $bridgeScript -BaseUrl "http://127.0.0.1:8000" -N8nUrl $N8nUrl -BridgeUrl $BridgeUrl -BrowserUrl $BrowserUrl
}

[pscustomobject]@{
    smoke_report = $smokeOut
    browse_report = $browseOut
    hydra_armor_report = "artifacts/system_smoke/hydra_armor_bridge_run.json"
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 5
