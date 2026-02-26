param(
  [string]$WorkspacePath = "",
  [string]$Agent = "Codex",
  [string]$Task = "unspecified",
  [string]$Status = "done",
  [string]$Summary = "",
  [string[]]$Artifacts = @(),
  [string]$Next = ""
)

$ErrorActionPreference = "Stop"

if (-not $WorkspacePath) {
  $defaultPathFile = Join-Path $env:USERPROFILE ".codex\obsidian_default_path.txt"
  if (Test-Path $defaultPathFile) {
    $WorkspacePath = (Get-Content -Path $defaultPathFile -Raw).Trim()
  }
}

if (-not $WorkspacePath) {
  $WorkspacePath = "C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace"
}

if (-not (Test-Path $WorkspacePath)) {
  throw "Workspace path not found: $WorkspacePath"
}

$crossTalkPath = Join-Path $WorkspacePath "Cross Talk.md"
$sessionsPath = Join-Path $WorkspacePath "Sessions"
New-Item -ItemType Directory -Force -Path $sessionsPath | Out-Null

$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")

if (-not $Summary) {
  $Summary = "No summary provided."
}

$artifactLines = @()
if ($Artifacts.Count -gt 0) {
  foreach ($a in $Artifacts) {
    if ($a) { $artifactLines += "- $a" }
  }
} else {
  $artifactLines += "- (none)"
}

$entry = @()
$entry += "## $utc | $Agent | $Task"
$entry += ""
$entry += "- status: $Status"
$entry += "- summary: $Summary"
$entry += "- artifacts:"
$entry += $artifactLines
if ($Next) {
  $entry += "- next: $Next"
}
$entry += ""

if (-not (Test-Path $crossTalkPath)) {
  @(
    "# Cross Talk",
    "",
    "- Use this note for inter-AI handoffs.",
    "- Keep updates short and execution-focused.",
    ""
  ) | Set-Content -Path $crossTalkPath -Encoding UTF8
}

Add-Content -Path $crossTalkPath -Value ($entry -join "`n") -Encoding UTF8

$sessionFile = Join-Path $sessionsPath "$stamp-$($Agent.ToLowerInvariant())-handoff.md"
$sessionLines = @(
  "# Session Handoff",
  "",
  "- timestamp_utc: $utc",
  "- agent: $Agent",
  "- task: $Task",
  "- status: $Status",
  "- summary: $Summary",
  "",
  "## Artifacts",
  ""
)
$sessionLines += $artifactLines
if ($Next) {
  $sessionLines += ""
  $sessionLines += "## Next"
  $sessionLines += ""
  $sessionLines += $Next
}
$sessionLines += ""
$sessionLines | Set-Content -Path $sessionFile -Encoding UTF8

Write-Host "Cross-talk updated: $crossTalkPath"
Write-Host "Session handoff: $sessionFile"

