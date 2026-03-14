param(
  [string]$WorkspacePath = "",
  [string]$Agent = "Codex",
  [string]$Callsign = "Helix Warden",
  [ValidateSet("active", "verified", "retired")]
  [string]$Status = "active",
  [string]$SessionId = "",
  [string]$Summary = "Session sign-on.",
  [int]$MaxVerifiedToKeep = 20,
  [int]$MaxRetiredToKeep = 10
)

$ErrorActionPreference = "Stop"

function Get-DefaultWorkspacePath {
  $defaultPathFile = Join-Path $env:USERPROFILE ".codex\obsidian_default_path.txt"
  if (Test-Path $defaultPathFile) {
    $value = (Get-Content -Path $defaultPathFile -Raw).Trim()
    if ($value) { return $value }
  }
  return "C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace"
}

function Normalize-Token([string]$Value) {
  if (-not $Value) { return "unknown" }
  $token = $Value.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
  $token = $token.Trim("-")
  if (-not $token) { return "unknown" }
  return $token
}

if (-not $WorkspacePath) {
  $WorkspacePath = Get-DefaultWorkspacePath
}
if (-not (Test-Path $WorkspacePath)) {
  throw "Workspace path not found: $WorkspacePath"
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $here "..\..")).Path

$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$agentToken = Normalize-Token $Agent
$callsignToken = Normalize-Token $Callsign
if (-not $SessionId) {
  $SessionId = "{0}-{1}-{2}" -f ((Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")), $agentToken, $callsignToken
}

$crossTalkPath = Join-Path $WorkspacePath "Cross Talk.md"
$sessionsPath = Join-Path $WorkspacePath "Sessions"
New-Item -ItemType Directory -Force -Path $sessionsPath | Out-Null

$repoNotesPath = Join-Path $repoRoot "notes\session_signons.md"
$repoLanePath = Join-Path $repoRoot "artifacts\agent_comm\session_signons.jsonl"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $repoLanePath) | Out-Null

$record = [ordered]@{
  timestamp_utc = $utc
  agent = $Agent
  callsign = $Callsign
  status = $Status
  session_id = $SessionId
  summary = $Summary
  workspace_path = $WorkspacePath
}
Add-Content -Path $repoLanePath -Value (($record | ConvertTo-Json -Compress)) -Encoding UTF8

$rows = @()
if (Test-Path $repoLanePath) {
  foreach ($line in Get-Content -Path $repoLanePath) {
    if (-not $line.Trim()) { continue }
    try {
      $obj = $line | ConvertFrom-Json
      if ($obj) { $rows += $obj }
    } catch {}
  }
}

# Keep latest record per session id
$latestBySession = @()
$seen = @{}
foreach ($r in ($rows | Sort-Object timestamp_utc -Descending)) {
  $sid = [string]$r.session_id
  if (-not $sid) { continue }
  if (-not $seen.ContainsKey($sid)) {
    $seen[$sid] = $true
    $latestBySession += $r
  }
}

$activeRows = @($latestBySession | Where-Object { $_.status -eq "active" } | Sort-Object timestamp_utc -Descending)
$verifiedRows = @($latestBySession | Where-Object { $_.status -eq "verified" } | Sort-Object timestamp_utc -Descending | Select-Object -First $MaxVerifiedToKeep)
$retiredRows = @($latestBySession | Where-Object { $_.status -eq "retired" } | Sort-Object timestamp_utc -Descending | Select-Object -First $MaxRetiredToKeep)
$visibleRows = @($activeRows + $verifiedRows + $retiredRows | Sort-Object timestamp_utc -Descending)

$note = @()
$note += "# Session Sign-Ons"
$note += ""
$note += "- Generated UTC: $utc"
$note += "- Rule: every AI signs on once per session with callsign + UTC timestamp."
$note += '- Rule: when work is validated, mark that session as `verified`.'
$note += '- Compaction: only latest verified/retired sessions are shown here; full ledger stays in `artifacts/agent_comm/session_signons.jsonl`.'
$note += ""
$note += "| timestamp_utc | agent | callsign | session_id | status | summary |"
$note += "|---|---|---|---|---|---|"
foreach ($r in $visibleRows) {
  $ts = [string]$r.timestamp_utc
  $ag = [string]$r.agent
  $cs = [string]$r.callsign
  $sid = [string]$r.session_id
  $st = [string]$r.status
  $sm = ([string]$r.summary).Replace("|", "/")
  $note += "| $ts | $ag | $cs | $sid | $st | $sm |"
}
$note += ""
$note | Set-Content -Path $repoNotesPath -Encoding UTF8

if (-not (Test-Path $crossTalkPath)) {
  @(
    "# Cross Talk",
    "",
    "- Use this note for inter-AI handoffs.",
    "- Keep updates short and execution-focused.",
    ""
  ) | Set-Content -Path $crossTalkPath -Encoding UTF8
}

$crossText = Get-Content -Path $crossTalkPath -Raw
if ($crossText -notmatch "Session Sign-On Protocol") {
  $protocol = @(
    "## Session Sign-On Protocol",
    "",
    "- Every AI writes one session sign-on with callsign + UTC timestamp.",
    '- Use: `scripts/system/session_signon.ps1`.',
    "- When a session's work is validated, rerun with -Status verified.",
    '- Older verified sign-ons are compacted in `notes/session_signons.md` while full history remains in `artifacts/agent_comm/session_signons.jsonl`.',
    ""
  )
  Add-Content -Path $crossTalkPath -Value ($protocol -join "`n") -Encoding UTF8
}

$entry = @(
  "## $utc | $Agent | session-sign-on",
  "",
  "- status: $Status",
  "- callsign: $Callsign",
  "- session_id: $SessionId",
  "- summary: $Summary",
  "- artifacts:",
  "  - notes/session_signons.md",
  "  - artifacts/agent_comm/session_signons.jsonl",
  ""
)
Add-Content -Path $crossTalkPath -Value ($entry -join "`n") -Encoding UTF8

$sessionFile = Join-Path $sessionsPath "$stamp-$agentToken-signon.md"
$sessionLines = @(
  "# Session Sign-On",
  "",
  "- timestamp_utc: $utc",
  "- agent: $Agent",
  "- callsign: $Callsign",
  "- session_id: $SessionId",
  "- status: $Status",
  "- summary: $Summary",
  "- repo_tracker: $repoNotesPath",
  "- repo_lane: $repoLanePath",
  ""
)
$sessionLines | Set-Content -Path $sessionFile -Encoding UTF8

Write-Host "Session sign-on appended."
Write-Host "Cross Talk: $crossTalkPath"
Write-Host "Session note: $sessionFile"
Write-Host "Repo tracker: $repoNotesPath"
Write-Host "Repo lane: $repoLanePath"
