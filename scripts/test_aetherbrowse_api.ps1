param(
    [string]$SCBEKey = "",
    [string]$BaseUrl = "http://127.0.0.1:8001",
    [string]$SessionId = "test-session-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($SCBEKey)) {
    $SCBEKey = ($env:SCBE_API_KEY | ForEach-Object { $_.Trim() } | Where-Object { $_ })[0]
}
if ([string]::IsNullOrWhiteSpace($SCBEKey)) {
    throw "SCBE API key missing. Set SCBE_API_KEY or pass -SCBEKey."
}

$headers = @{
    "X-API-Key"   = $SCBEKey
    "Content-Type" = "application/json"
}

$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" -TimeoutSec 20
Write-Host "Health:" -ForegroundColor Cyan
$health | ConvertTo-Json -Depth 10

$bodyObj = @{
    actions = @(
        @{
            action = "navigate"
            target = "https://example.com"
            timeout_ms = 10000
        },
        @{
            action = "screenshot"
            target = "full_page"
            timeout_ms = 12000
        }
    )
    session_id = $SessionId
}

$body = $bodyObj | ConvertTo-Json -Depth 10
$result = Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/integrations/n8n/browse" -Headers $headers -Body $body -TimeoutSec 120

Write-Host ""
Write-Host "Browse result:" -ForegroundColor Green
$result | ConvertTo-Json -Depth 10
