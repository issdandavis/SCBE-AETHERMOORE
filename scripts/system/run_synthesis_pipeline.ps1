param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$BridgeUrl = "http://127.0.0.1:8002",
    [string]$BrowserUrl = "http://127.0.0.1:8012",
    [string]$N8nUrl = "http://127.0.0.1:5680",
    [string]$BrowseUrl = ""
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$evidenceDir = Join-Path $RepoRoot "artifacts\page_evidence"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

$smokeOut = Join-Path $RepoRoot "artifacts\system_smoke\synthesis_smoke.json"
python scripts/system/full_system_smoke.py --bridge-url $BridgeUrl --browser-url $BrowserUrl --n8n-url $N8nUrl --probe-webhook --output $smokeOut
if ($LASTEXITCODE -ne 0) {
    throw "Synthesis smoke failed."
}

$browseOut = Join-Path $evidenceDir "synthesis_terminal_browse.json"
$nodeBrowseScript = "C:\Users\issda\.codex\skills\hydra-node-terminal-browsing\scripts\hydra_terminal_browse.mjs"
if (Test-Path $nodeBrowseScript) {
    if ([string]::IsNullOrWhiteSpace($BrowseUrl)) {
        $BrowseUrl = $N8nUrl
    }
    node $nodeBrowseScript --url $BrowseUrl --out $browseOut
}

$bridgeScript = Join-Path $RepoRoot "scripts\system\run_hydra_armor_bridge.ps1"
$bridgeResult = $null
if (Test-Path $bridgeScript) {
    $bridgeRaw = (& $bridgeScript -RepoRoot $RepoRoot -N8nUrl $N8nUrl -BridgeUrl $BridgeUrl -BrowserUrl $BrowserUrl | Out-String).Trim()
    try {
        $bridgeResult = $bridgeRaw | ConvertFrom-Json
    } catch {
        # Allow scripts that print status logs before emitting JSON payload.
        $lines = $bridgeRaw -split "(`r`n|`n|`r)"
        $jsonStart = -1
        for ($i = $lines.Length - 1; $i -ge 0; $i--) {
            if ($lines[$i] -match "^\s*\{") {
                $jsonStart = $i
                break
            }
        }
        if ($jsonStart -ge 0) {
            $jsonText = ($lines[$jsonStart..($lines.Length - 1)] -join [Environment]::NewLine).Trim()
            $bridgeResult = $jsonText | ConvertFrom-Json
        } else {
            throw
        }
    }
}

$summary = [ordered]@{
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    smoke_report = $smokeOut
    browse_report = $browseOut
    hydra_armor = $bridgeResult
}

$summaryOut = Join-Path $RepoRoot "artifacts\system_smoke\synthesis_summary.json"
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryOut
$summary | ConvertTo-Json -Depth 8
