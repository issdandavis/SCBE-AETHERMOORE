# Install / register the youtube-data-mcp-server with Claude Code.
#
# Reads client_id and client_secret out of your local client_secrets.json
# (default: $env:USERPROFILE\.secrets\youtube\client_secrets.json), then
# registers the MCP server with `claude mcp add` so it's available in every
# Claude Code session.
#
# Usage:
#   pwsh scripts/video/install_youtube_mcp.ps1
#   pwsh scripts/video/install_youtube_mcp.ps1 -ClientSecretsPath "C:\Path\to\client_secrets.json"
#
# After running this once, restart Claude Code and the MCP server should
# appear in `claude mcp list`.

param(
    [string]$ClientSecretsPath = "$env:USERPROFILE\.secrets\youtube\client_secrets.json",
    [string]$ServerName = "youtube"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ClientSecretsPath)) {
    Write-Host "ERROR: client_secrets.json not found at: $ClientSecretsPath" -ForegroundColor Red
    Write-Host "Move your downloaded Google OAuth client_secret_*.json to that path first."
    exit 1
}

$json = Get-Content -Raw -Path $ClientSecretsPath | ConvertFrom-Json

# Google OAuth client_secrets.json wraps the credentials in either an
# "installed" or "web" object depending on the application type.
if ($json.installed) {
    $creds = $json.installed
} elseif ($json.web) {
    $creds = $json.web
} else {
    Write-Host "ERROR: client_secrets.json missing 'installed' or 'web' section." -ForegroundColor Red
    exit 2
}

$clientId = $creds.client_id
$clientSecret = $creds.client_secret

if (-not $clientId -or -not $clientSecret) {
    Write-Host "ERROR: client_id or client_secret missing from $ClientSecretsPath" -ForegroundColor Red
    exit 3
}

Write-Host "Registering MCP server '$ServerName' with Claude Code..."
Write-Host "  client_id (first 16 chars): $($clientId.Substring(0, [Math]::Min(16, $clientId.Length)))..."

# Remove any existing entry so this is idempotent.
& claude mcp remove $ServerName 2>$null | Out-Null

& claude mcp add `
    -e "YOUTUBE_CLIENT_ID=$clientId" `
    -e "YOUTUBE_CLIENT_SECRET=$clientSecret" `
    $ServerName -- npx -y youtube-data-mcp-server

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "OK: registered. Restart Claude Code, then run 'claude mcp list' to confirm." -ForegroundColor Green
    Write-Host "After restart, the youtube-data-mcp-server tools become available in chat."
} else {
    Write-Host ""
    Write-Host "ERROR: claude mcp add failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
