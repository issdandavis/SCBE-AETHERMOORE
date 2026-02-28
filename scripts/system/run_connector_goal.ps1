param(
    [string]$Goal = "connector run",
    [string]$ConnectorName = "zapier-main-hook",
    [string]$Channel = "web_research",
    [string]$Priority = "normal",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ApiKey = "",
    [int]$AdvanceSteps = 6,
    [int]$DelayMs = 500
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:SCBE_MOBILE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:SCBE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = "demo_key_12345"
}

$headers = @{
    "x-api-key"    = $ApiKey
    "Content-Type" = "application/json"
}

function Invoke-ScbeApi {
    param(
        [string]$Method,
        [string]$Path,
        [string]$Body = ""
    )
    $url = "{0}{1}" -f $BaseUrl.TrimEnd("/"), $Path
    if ([string]::IsNullOrWhiteSpace($Body)) {
        return Invoke-RestMethod -Method $Method -Uri $url -Headers $headers
    }
    return Invoke-RestMethod -Method $Method -Uri $url -Headers $headers -Body $Body
}

$list = Invoke-ScbeApi -Method "GET" -Path "/mobile/connectors"
$matches = @($list.data | Where-Object { $_.name -eq $ConnectorName })
if ($matches.Count -eq 0) {
    throw "Connector not found: $ConnectorName"
}

$connector = $matches | Sort-Object -Property created_at -Descending | Select-Object -First 1
$connectorId = $connector.connector_id

$payload = @{
    goal                        = $Goal
    channel                     = $Channel
    priority                    = $Priority
    execution_mode              = "connector"
    connector_id                = $connectorId
    require_human_for_high_risk = $false
} | ConvertTo-Json -Compress

$create = Invoke-ScbeApi -Method "POST" -Path "/mobile/goals" -Body $payload
$goalId = $create.data.goal_id
if (-not $goalId) {
    throw "Goal creation did not return a goal_id."
}

for ($i = 0; $i -lt $AdvanceSteps; $i++) {
    $adv = Invoke-ScbeApi -Method "POST" -Path "/mobile/goals/$goalId/advance" -Body "{}"
    $state = $adv.data.goal_state
    if ($state -in @("completed", "failed", "review_required")) {
        break
    }
    Start-Sleep -Milliseconds $DelayMs
}

$final = Invoke-ScbeApi -Method "GET" -Path "/mobile/goals/$goalId"

[pscustomobject]@{
    goal_id       = $goalId
    goal          = $Goal
    connector     = $ConnectorName
    connector_id  = $connectorId
    endpoint_url  = $connector.endpoint_url
    status        = $final.data.status
    current_step  = $final.data.current_step_index
    events        = $final.data.events.Count
} | ConvertTo-Json -Depth 6
