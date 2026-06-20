# Weekly USPTO prosecution monitor for SCBE-2026-0001 (App 19/691,526)
# Scheduled: every Wednesday 09:00 local
# Log:        artifacts/patent_monitor/monitor_run.log
#
# First run will fail until:
#   1. USPTO_ODP_API_KEY is set in .env.connector.oauth
#   2. Application 19691526 appears in ODP (24-72h after filing)

$repoRoot = "C:\Users\issda\SCBE-AETHERMOORE"
$envFile  = "$repoRoot\config\connector_oauth\.env.connector.oauth"
$logFile  = "$repoRoot\artifacts\patent_monitor\monitor_run.log"
$app      = "19691526"

# Load .env key
$key = (Get-Content $envFile -ErrorAction SilentlyContinue | Where-Object { $_ -match "^USPTO_ODP_API_KEY=" } | Select-Object -First 1) -replace "^USPTO_ODP_API_KEY=",""
if (-not $key -or $key -eq "REPLACE_ME") {
    Add-Content $logFile "[$(Get-Date -Format 'u')] SKIP: USPTO_ODP_API_KEY not set — register at https://developer.uspto.gov"
    Write-Host "USPTO_ODP_API_KEY not set. Register at https://developer.uspto.gov"
    exit 0
}

$env:USPTO_ODP_API_KEY = $key

$timestamp = Get-Date -Format "u"
Add-Content $logFile "`n[$timestamp] === Patent monitor run ==="

$output = python "$repoRoot\scripts\system\uspto_prosecution_monitor.py" --app $app 2>&1
Add-Content $logFile ($output | Out-String)

if ($LASTEXITCODE -eq 1) {
    Write-Host "CHANGES DETECTED — check $logFile"
    Add-Content $logFile "[$timestamp] ACTION REQUIRED: prosecution state changed"
} elseif ($LASTEXITCODE -eq 2) {
    Add-Content $logFile "[$timestamp] FETCH ERROR — check network/API key"
} else {
    Add-Content $logFile "[$timestamp] No changes."
}
