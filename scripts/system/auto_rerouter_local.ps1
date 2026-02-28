param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$N8nUserFolder = "C:\Users\issda\SCBE-AETHERMOORE\.n8n_local",
    [int]$BridgePort = 8001,
    [int]$BrowserPort = 8011,
    [int]$N8nPort = 5678,
    [int]$N8nTaskBrokerPort = 5679,
    [string[]]$PreferredProviders = @("xai", "anthropic", "openai", "huggingface"),
    [switch]$RestartIfMissing,
    [switch]$ImportWorkflows,
    [switch]$PublishWorkflows,
    [switch]$OutputJson
)

$ErrorActionPreference = "Stop"

function Get-BridgeApiKey {
    if ($env:SCBE_API_KEY) {
        return $env:SCBE_API_KEY
    }
    if ($env:SCBE_API_KEYS) {
        $first = ($env:SCBE_API_KEYS -split ",")[0].Trim()
        if ($first) { return $first }
    }
    return "scbe-dev-key"
}

function Test-Http {
    param(
        [string]$Url,
        [int]$TimeoutSec = 5
    )
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Get-ProviderStatus {
    param(
        [string]$BridgeBaseUrl,
        [string]$ApiKey
    )
    try {
        return Invoke-RestMethod `
            -Method Get `
            -Uri "$BridgeBaseUrl/v1/llm/providers" `
            -Headers @{ "X-API-Key" = $ApiKey } `
            -TimeoutSec 8
    } catch {
        return $null
    }
}

function Stop-Ports {
    param([int[]]$Ports)
    $procIds = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalPort -in $Ports } |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($procId in $procIds) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host "Stopped process $procId on target ports."
        } catch {
            Write-Warning "Failed to stop process ${procId}: $($_.Exception.Message)"
        }
    }
}

function Restart-Stack {
    param(
        [string]$Root,
        [string]$UserFolder,
        [int]$Bridge,
        [int]$Browser,
        [int]$N8n,
        [int]$Broker,
        [bool]$DoImport,
        [bool]$DoPublish
    )
    $startScript = Join-Path $Root "workflows\n8n\start_n8n_local.ps1"
    if (-not (Test-Path $startScript)) {
        throw "Missing start script: $startScript"
    }

    Stop-Ports -Ports @($Bridge, $Browser, $N8n, $Broker)
    Start-Sleep -Seconds 2

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $startScript,
        "-ProjectRoot", $Root,
        "-N8nUserFolder", $UserFolder,
        "-BridgePort", "$Bridge",
        "-BrowserPort", "$Browser",
        "-N8nPort", "$N8n",
        "-N8nTaskBrokerPort", "$Broker",
        "-StartBrowserAgent"
    )
    if ($DoImport) { $args += "-ImportWorkflows" }
    if ($DoPublish) { $args += "-PublishWorkflows" }

    & powershell.exe @args
}

$bridgeBase = "http://127.0.0.1:$BridgePort"
$bridgeHealthUrl = "$bridgeBase/health"
$providersUrl = "$bridgeBase/v1/llm/providers"
$apiKey = Get-BridgeApiKey

$bridgeHealthy = Test-Http -Url $bridgeHealthUrl
$providerStatus = Get-ProviderStatus -BridgeBaseUrl $bridgeBase -ApiKey $apiKey

if ((-not $bridgeHealthy -or -not $providerStatus) -and $RestartIfMissing) {
    Write-Host "Bridge or provider router unavailable. Restarting local stack..."
    Restart-Stack `
        -Root $ProjectRoot `
        -UserFolder $N8nUserFolder `
        -Bridge $BridgePort `
        -Browser $BrowserPort `
        -N8n $N8nPort `
        -Broker $N8nTaskBrokerPort `
        -DoImport:$ImportWorkflows `
        -DoPublish:$PublishWorkflows

    Start-Sleep -Seconds 4
    $bridgeHealthy = Test-Http -Url $bridgeHealthUrl
    $providerStatus = Get-ProviderStatus -BridgeBaseUrl $bridgeBase -ApiKey $apiKey
}

$configured = @()
if ($providerStatus -and $providerStatus.providers) {
    foreach ($p in @("xai", "anthropic", "openai", "huggingface")) {
        $node = $providerStatus.providers.$p
        if ($node -and $node.configured) {
            $configured += $p
        }
    }
}

$selected = $null
foreach ($pref in $PreferredProviders) {
    if ($configured -contains $pref) {
        $selected = $pref
        break
    }
}
if (-not $selected -and $configured.Count -gt 0) {
    $selected = $configured[0]
}
if (-not $selected) {
    $selected = "huggingface"
}

$env:SCBE_ROUTER_PROVIDER = $selected

$out = [ordered]@{
    status = if ($bridgeHealthy -and $providerStatus) { "ok" } else { "degraded" }
    bridge = @{
        base_url = $bridgeBase
        health_url = $bridgeHealthUrl
        providers_url = $providersUrl
        healthy = $bridgeHealthy
    }
    selected_provider = $selected
    configured_providers = $configured
    preferred_order = $PreferredProviders
    api_key_source = if ($env:SCBE_API_KEY) { "SCBE_API_KEY" } elseif ($env:SCBE_API_KEYS) { "SCBE_API_KEYS(first)" } else { "default(scbe-dev-key)" }
    env = @{
        SCBE_ROUTER_PROVIDER = $env:SCBE_ROUTER_PROVIDER
    }
}

if ($OutputJson) {
    $out | ConvertTo-Json -Depth 8
} else {
    Write-Host "Auto re-router complete."
    Write-Host ("Bridge healthy: {0}" -f $out.bridge.healthy)
    Write-Host ("Configured providers: {0}" -f (($configured -join ", ") -replace "^$", "(none)"))
    Write-Host ("Selected provider: {0}" -f $selected)
    Write-Host "Env set: SCBE_ROUTER_PROVIDER=$($env:SCBE_ROUTER_PROVIDER)"
}

if (-not ($bridgeHealthy -and $providerStatus)) {
    exit 1
}
exit 0

