param(
  [string]$WorkspacePath = "C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace",
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

$payloadObj = [ordered]@{
  summary = $Summary
  recipient = $Recipient
  sender = $Sender
  intent = $Intent
  status = $Status
  task_id = $TaskId
  next_action = $NextAction
  risk = $Risk
  repo = $Repo
  branch = $Branch
  proof = $Proof
  session_id = $SessionId
  codename = $Codename
  where = $Where
  why = $Why
  how = $How
}

$payloadJson = ($payloadObj | ConvertTo-Json -Depth 8 -Compress)

$py = @"
import json
from src.aethercode.gateway import CrossTalkRequest, _write_crosstalk_packet

payload = json.loads(r'''$payloadJson''')
req = CrossTalkRequest(**payload)
res = _write_crosstalk_packet(req)
print(json.dumps({
    "packet_id": res["packet"]["packet_id"],
    "packet_path": str(res["packet_path"]),
    "line": res["line"],
}))
"@

$packetOut = $py | python -
if ($LASTEXITCODE -ne 0) {
  throw "Packet emission failed."
}

$packet = $packetOut | ConvertFrom-Json

& (Join-Path $repoRoot "scripts\system\cross_talk_append.ps1") `
  -WorkspacePath $WorkspacePath `
  -Agent "Codex" `
  -Task $TaskId `
  -Status $Status `
  -Summary $Summary `
  -Artifacts @($packet.packet_path) `
  -Next $NextAction `
  -SessionId $SessionId `
  -Codename $Codename `
  -Where $Where `
  -Why $Why `
  -How $How

if ($LASTEXITCODE -ne 0) {
  throw "Obsidian cross-talk append failed."
}

[pscustomobject]@{
  ok = $true
  session_id = $SessionId
  codename = $Codename
  packet_id = $packet.packet_id
  packet_path = $packet.packet_path
  workspace = $WorkspacePath
} | ConvertTo-Json -Depth 4
