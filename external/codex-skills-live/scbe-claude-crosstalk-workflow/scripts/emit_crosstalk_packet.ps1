param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [switch]$NewSession,
    [string]$SessionId = "",
    [string]$Codename = "",
    [string]$Sender = "agent.codex",
    [string]$Recipient = "agent.claude",
    [Parameter(Mandatory = $true)][string]$TaskId,
    [Parameter(Mandatory = $true)][string]$Summary,
    [ValidateSet("in_progress", "blocked", "done", "verify")]
    [string]$Status = "in_progress",
    [string]$NextAction = "",
    [string]$Where = "",
    [string]$Why = "",
    [string]$How = "",
    [ValidateSet("low", "medium", "high")]
    [string]$Risk = "low",
    [string[]]$Proof = @()
)

$ErrorActionPreference = "Stop"

function Get-UtcIso {
    return (Get-Date).ToUniversalTime().ToString("o")
}

function Get-UtcStamp {
    return (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
}

function Get-UtcDay {
    return (Get-Date).ToUniversalTime().ToString("yyyyMMdd")
}

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Normalize-Name([string]$Value, [string]$Fallback) {
    $text = ""
    if ($null -ne $Value) {
        $text = "$Value"
    }
    $text = $text.Trim().ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($text)) {
        $text = $Fallback
    }
    $text = [regex]::Replace($text, "[^a-z0-9._-]+", "-")
    $text = $text.Trim("-")
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $Fallback
    }
    return $text
}

function New-Codename {
    $adjectives = @("steady", "clear", "silver", "ember", "tidal", "stone", "quiet", "north")
    $nouns = @("otter", "falcon", "lantern", "reef", "harbor", "signal", "anchor", "compass")
    $a = Get-Random -InputObject $adjectives
    $n = Get-Random -InputObject $nouns
    return "$a-$n"
}

$repo = (Resolve-Path -Path $RepoRoot).Path
$day = Get-UtcDay
$stamp = Get-UtcStamp

$dayDir = Join-Path $repo "artifacts\agent_comm\$day"
$laneDir = Join-Path $repo "artifacts\agent_comm\github_lanes"
$stateDir = Join-Path $repo "artifacts\agent_comm\session_state"
$notesDir = Join-Path $repo "notes"
$inboxPath = Join-Path $notesDir "_inbox.md"
$lanePath = Join-Path $laneDir "cross_talk.jsonl"

Ensure-Dir $dayDir
Ensure-Dir $laneDir
Ensure-Dir $stateDir
Ensure-Dir $notesDir

$senderSlug = Normalize-Name -Value $Sender -Fallback "agent"
$taskSlug = Normalize-Name -Value $TaskId -Fallback "task"
$stateFile = Join-Path $stateDir ("{0}.json" -f $senderSlug)

$activeSessionId = ""
$activeCodename = ""

if (-not [string]::IsNullOrWhiteSpace($SessionId)) {
    $activeSessionId = $SessionId.Trim()
}
if (-not [string]::IsNullOrWhiteSpace($Codename)) {
    $activeCodename = $Codename.Trim()
}

if (($NewSession -or [string]::IsNullOrWhiteSpace($activeSessionId) -or [string]::IsNullOrWhiteSpace($activeCodename)) -and (Test-Path $stateFile)) {
    try {
        $stateObj = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
        if (-not $NewSession) {
            if ([string]::IsNullOrWhiteSpace($activeSessionId)) { $activeSessionId = "$($stateObj.session_id)" }
            if ([string]::IsNullOrWhiteSpace($activeCodename)) { $activeCodename = "$($stateObj.codename)" }
        }
    }
    catch {
    }
}

if ($NewSession -or [string]::IsNullOrWhiteSpace($activeSessionId)) {
    $activeSessionId = [Guid]::NewGuid().ToString("N")
}
if ($NewSession -or [string]::IsNullOrWhiteSpace($activeCodename)) {
    $activeCodename = New-Codename
}

$statePayload = [ordered]@{
    sender = $Sender
    session_id = $activeSessionId
    codename = $activeCodename
    updated_at = Get-UtcIso
}
$statePayload | ConvertTo-Json -Depth 10 | Set-Content -Path $stateFile -Encoding UTF8

$packetId = "cross-talk-{0}-{1}-{2}" -f $senderSlug, $taskSlug, $stamp
$packet = [ordered]@{
    packet_id = $packetId
    session_id = $activeSessionId
    codename = $activeCodename
    created_at = Get-UtcIso
    sender = $Sender
    recipient = $Recipient
    task_id = $TaskId
    summary = $Summary
    status = $Status
    next_action = $NextAction
    where = $Where
    why = $Why
    how = $How
    risk = $Risk
    proof = @($Proof)
}

$packetFile = Join-Path $dayDir ("{0}.json" -f $packetId)
$packet | ConvertTo-Json -Depth 12 | Set-Content -Path $packetFile -Encoding UTF8

$packetJsonl = $packet | ConvertTo-Json -Depth 12 -Compress
Add-Content -Path $lanePath -Value $packetJsonl -Encoding UTF8

$line = "- [{0}] {1} -> {2} | {3} | {4} | {5}" -f (Get-UtcIso), $Sender, $Recipient, $TaskId, $Status, $Summary
if (-not (Test-Path $inboxPath)) {
    "# Inbox`n" | Set-Content -Path $inboxPath -Encoding UTF8
}
Add-Content -Path $inboxPath -Value $line -Encoding UTF8

$result = [ordered]@{
    ok = $true
    packet_id = $packetId
    packet_file = $packetFile
    lane_file = $lanePath
    inbox_file = $inboxPath
    session_id = $activeSessionId
    codename = $activeCodename
}
$result | ConvertTo-Json -Depth 8
