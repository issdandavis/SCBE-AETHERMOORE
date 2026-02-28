param(
    [ValidateSet("free", "paid", "all")]
    [string]$Profile = "all",
    [string]$OutputPath = "config/connector_oauth/.env.connector.oauth",
    [switch]$IncludeCurrentSession,
    [switch]$PrintStatus
)

$ErrorActionPreference = "Stop"

function Get-EnvOrPlaceholder {
    param(
        [string]$Name,
        [string]$Placeholder = "REPLACE_ME"
    )
    if ($IncludeCurrentSession) {
        $value = (Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue).Value
        if ($value) { return $value }
    }
    return $Placeholder
}

$freeVars = @(
    "GITHUB_TOKEN",
    "NOTION_TOKEN",
    "NOTION_API_KEY",
    "HF_TOKEN",
    "GOOGLE_DRIVE_ACCESS_TOKEN",
    "AIRTABLE_TOKEN",
    "AIRTABLE_BASE_ID",
    "N8N_BASE_URL",
    "N8N_CONNECTOR_WEBHOOK_URL",
    "SCBE_BRIDGE_URL",
    "SCBE_BROWSER_URL",
    "GITHUB_ACTIONS_WEBHOOK_URL",
    "NOTION_CONNECTOR_WEBHOOK_URL",
    "AIRTABLE_CONNECTOR_WEBHOOK_URL",
    "HF_CONNECTOR_WEBHOOK_URL",
    "TELEGRAM_CONNECTOR_WEBHOOK_URL",
    "SCBE_TELEGRAM_WEBHOOK_URL",
    "TELEGRAM_BOT_TOKEN",
    "SCBE_TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "SCBE_TELEGRAM_CHAT_ID",
    "SCBE_API_KEY",
    "ZAPIER_WEBHOOK_URL"
)

$paidVars = @(
    "SHOPIFY_ACCESS_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "SLACK_BOT_TOKEN",
    "DISCORD_BOT_TOKEN",
    "LINEAR_API_KEY",
    "ASANA_PAT",
    "STRIPE_API_KEY",
    "DROPBOX_ACCESS_TOKEN",
    "SHOPIFY_SHOP_DOMAIN",
    "SHOPIFY_API_VERSION",
    "SLACK_CONNECTOR_WEBHOOK_URL",
    "LINEAR_CONNECTOR_WEBHOOK_URL",
    "DISCORD_CONNECTOR_WEBHOOK_URL",
    "ASANA_CONNECTOR_WEBHOOK_URL",
    "STRIPE_CONNECTOR_WEBHOOK_URL"
)

$selected = switch ($Profile) {
    "free" { $freeVars }
    "paid" { $paidVars }
    default { $freeVars + $paidVars }
}

$header = @(
    "# SCBE Connector OAuth Bootstrap",
    "# Generated: $(Get-Date -Format o)",
    "# Profile: $Profile",
    "# Load this file into your session env before running connector checks.",
    ""
)

$lines = New-Object System.Collections.Generic.List[string]
$header | ForEach-Object { [void]$lines.Add($_) }

foreach ($name in $selected) {
    $value = Get-EnvOrPlaceholder -Name $name
    [void]$lines.Add("$name=$value")
}

$fullOutputPath = Join-Path (Get-Location) $OutputPath
$outputDir = Split-Path -Parent $fullOutputPath
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$lines -join "`n" | Set-Content -Path $fullOutputPath -Encoding UTF8
Write-Host "[SCBE] OAuth template written: $fullOutputPath"

Write-Host ""
Write-Host "[SCBE] Next command (free + infra health):"
Write-Host "python scripts/connector_health_check.py --checks github notion drive huggingface airtable n8n bridge playwright zapier telegram --n8n-base-url http://127.0.0.1:5680 --bridge-base-url http://127.0.0.1:8002 --playwright-base-url http://127.0.0.1:8012 --output artifacts/connector_health/fleet_connector_health.json"
Write-Host ""
Write-Host "[SCBE] Register connectors (free profile):"
Write-Host "powershell -ExecutionPolicy Bypass -File scripts/system/register_connector_profiles.ps1 -Profile free -BaseUrl http://127.0.0.1:8000 -N8nBaseUrl http://127.0.0.1:5680"
Write-Host "[SCBE] Register connectors (paid profile):"
Write-Host "powershell -ExecutionPolicy Bypass -File scripts/system/register_connector_profiles.ps1 -Profile paid -BaseUrl http://127.0.0.1:8000 -N8nBaseUrl http://127.0.0.1:5680"

if ($PrintStatus) {
    Write-Host ""
    Write-Host "[SCBE] Local auth status snapshot:"

    $gh = "not_installed"
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        try {
            $ghUser = gh api user --jq .login 2>$null
            if ($ghUser) { $gh = "ok:$ghUser" } else { $gh = "installed_not_authed" }
        } catch {
            $gh = "installed_not_authed"
        }
    }
    Write-Host "  GitHub CLI: $gh"

    $hf = "not_installed"
    if (Get-Command hf -ErrorAction SilentlyContinue) {
        try {
            $hfUser = hf auth whoami 2>$null
            if ($hfUser) { $hf = "ok" } else { $hf = "installed_not_authed" }
        } catch {
            $hf = "installed_not_authed"
        }
    }
    Write-Host "  Hugging Face CLI: $hf"

    $n8n = "not_installed"
    if (Get-Command n8n -ErrorAction SilentlyContinue -CommandType Application) {
        $n8n = "installed"
    } elseif (Get-Command n8n.cmd -ErrorAction SilentlyContinue -CommandType Application) {
        $n8n = "installed"
    }
    Write-Host "  n8n CLI: $n8n"
}
