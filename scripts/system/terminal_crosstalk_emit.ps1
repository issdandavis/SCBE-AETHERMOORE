param(
  [string]$WorkspacePath = "",
  [string]$Sender = "agent.codex",
  [string]$Recipient = "agent.claude",
  [string]$Intent = "handoff",
  [string]$Status = "in_progress",
  [string]$TaskId = "TERMINAL-CROSSTALK",
  [string]$Summary = "Terminal cross-talk update.",
  [string]$NextAction = "",
  [string]$Risk = "low",
  [string]$Repo = "SCBE-AETHERMOORE",
  [string]$Branch = "local",
  [string]$SessionId = "",
  [string]$Codename = "",
  [string]$Where = "terminal",
  [string]$Why = "",
  [string]$How = "",
  [string[]]$Proof = @(),
  [switch]$NewSession = $false
)

$ErrorActionPreference = "Stop"

function New-Codename {
  $left = @(
    "Lyra","Aether","Nova","Orion","Delta","Vega","Quartz","Echo","Atlas","Helix",
    "Rune","Polar","Drift","Pillar","Cipher","Summit","Vector","Pulse","Titan","Lumen"
  )
  $right = @(
    "Forge","Bridge","Signal","Anchor","Lane","Node","Track","Spire","Mesh","Scout",
    "Guard","Relay","Pilot","Beacon","Frame","Handoff","Glyph","Flux","Index","Harbor"
  )
  $a = $left | Get-Random
  $b = $right | Get-Random
  $n = Get-Random -Minimum 10 -Maximum 99
  return "$a-$b-$n"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

$stateDir = Join-Path $repoRoot ".scbe"
$statePath = Join-Path $stateDir "crosstalk_session_state.json"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$state = $null
if ((-not $NewSession) -and (Test-Path $statePath)) {
  try {
    $state = Get-Content -Path $statePath -Raw | ConvertFrom-Json
  } catch {
    $state = $null
  }
}

if (-not $SessionId) {
  if ($state -and $state.session_id) {
    $SessionId = [string]$state.session_id
  } else {
    $SessionId = "sess-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ") + "-" + ([Guid]::NewGuid().ToString("N").Substring(0, 6))
  }
}

if (-not $Codename) {
  if ($state -and $state.codename) {
    $Codename = [string]$state.codename
  } else {
    $Codename = New-Codename
  }
}

[pscustomobject]@{
  session_id = $SessionId
  codename = $Codename
  updated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json -Depth 3 | Set-Content -Path $statePath -Encoding UTF8

$senderAgent = $Sender -replace '^agent\.', ''
$recipientAgent = $Recipient -replace '^agent\.', ''
$artifactsArg = (($Proof | Where-Object { $_ -and $_.Trim() }) -join ",")

$opsArgs = @(
  "scripts/system/ops_control.py",
  "send",
  "--from", $senderAgent,
  "--to", $recipientAgent,
  "--intent", $Intent,
  "--status", $Status,
  "--summary", $Summary,
  "--json"
)

if ($NextAction) {
  $opsArgs += @("--next", $NextAction)
}
if ($TaskId) {
  $opsArgs += @("--task-id", $TaskId)
}
if ($Risk) {
  $opsArgs += @("--risk", $Risk)
}
if ($Where) {
  $opsArgs += @("--where", $Where)
}
if ($Why) {
  $opsArgs += @("--why", $Why)
}
if ($How) {
  $opsArgs += @("--how", $How)
}
if ($SessionId) {
  $opsArgs += @("--session-id", $SessionId)
}
if ($Codename) {
  $opsArgs += @("--codename", $Codename)
}
if ($WorkspacePath) {
  $opsArgs += @("--workspace", $WorkspacePath)
}

if ($artifactsArg) {
  $opsArgs += @("--artifacts", $artifactsArg)
}

$packetOut = & python @opsArgs
if ($LASTEXITCODE -ne 0) {
  throw "Packet emission failed."
}

$packet = $packetOut | ConvertFrom-Json

[pscustomobject]@{
  ok = $true
  session_id = $SessionId
  codename = $Codename
  packet_id = $packet.packet.packet_id
  packet_path = $packet.delivery.json_packet.detail
  workspace = $packet.workspace
} | ConvertTo-Json -Depth 4
