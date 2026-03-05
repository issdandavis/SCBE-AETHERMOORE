param(
  [string]$GatewayBaseUrl = "http://127.0.0.1:8500",
  [int]$Limit = 200
)

$ErrorActionPreference = "Stop"

if ($Limit -lt 1) { $Limit = 1 }
if ($Limit -gt 2000) { $Limit = 2000 }

$pendingUrl = "{0}/v1/crosstalk/pending?limit={1}" -f $GatewayBaseUrl.TrimEnd("/"), $Limit
$sessionsUrl = "{0}/v1/crosstalk/session-signons?limit={1}" -f $GatewayBaseUrl.TrimEnd("/"), $Limit

try {
  $pending = Invoke-RestMethod -Uri $pendingUrl -Method Get -TimeoutSec 30
} catch {
  throw "Failed to fetch pending cross-talk snapshot from $pendingUrl. $($_.Exception.Message)"
}

try {
  $sessions = Invoke-RestMethod -Uri $sessionsUrl -Method Get -TimeoutSec 30
} catch {
  throw "Failed to fetch session sign-on snapshot from $sessionsUrl. $($_.Exception.Message)"
}

Write-Host "== Cross-Talk Pending =="
Write-Host ("pending_count={0} total_tasks={1} total_records={2}" -f $pending.pending_count, $pending.total_tasks, $pending.total_records)
if ($pending.items -and $pending.items.Count -gt 0) {
  $pending.items | Select-Object created_at, task_id, status, sender, recipient, risk | Format-Table -AutoSize
} else {
  Write-Host "(no pending tasks)"
}

Write-Host ""
Write-Host "== Session Sign-Ons =="
$counts = $sessions.counts
Write-Host ("active={0} verified={1} retired={2} other={3} unique_sessions={4}" -f $counts.active, $counts.verified, $counts.retired, $counts.other, $sessions.unique_sessions)
if ($sessions.items -and $sessions.items.Count -gt 0) {
  $sessions.items | Select-Object timestamp_utc, session_id, agent, callsign, status | Format-Table -AutoSize
}

