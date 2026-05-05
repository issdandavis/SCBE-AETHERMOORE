param(
  [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
  [int]$Width = 100
)

# Hidden wrapper around night_training_watch.ps1 that appends a single char to
# a rolling heartbeat line. Always keeps the file <= $Width chars (default 100):
#
#   . = success (exit 0)
#   x = script failed (non-zero exit)
#   ? = wrapper-level error (couldn't even launch)
#
# Glance pattern: cat the file, you see the last 100 runs at a glance.

$ErrorActionPreference = "Continue"
$inner = Join-Path $RepoRoot "scripts\system\night_training_watch.ps1"
$beatDir = Join-Path $RepoRoot "artifacts\heartbeat"
$beatFile = Join-Path $beatDir "night_training_watch.line"
$null = New-Item -ItemType Directory -Path $beatDir -Force -ErrorAction SilentlyContinue

$char = "?"
try {
  if (Test-Path -LiteralPath $inner) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $inner *> $null
    $char = if ($LASTEXITCODE -eq 0) { "." } else { "x" }
  } else {
    $char = "?"
  }
} catch {
  $char = "?"
}

try {
  $existing = if (Test-Path -LiteralPath $beatFile) { (Get-Content -LiteralPath $beatFile -Raw -ErrorAction SilentlyContinue) } else { "" }
  if ($null -eq $existing) { $existing = "" }
  $existing = $existing.TrimEnd("`r", "`n")
  $combined = ($existing + $char)
  if ($combined.Length -gt $Width) {
    $combined = $combined.Substring($combined.Length - $Width, $Width)
  }
  Set-Content -LiteralPath $beatFile -Value $combined -NoNewline -Encoding ascii
} catch {
  # heartbeat write failed -- not fatal, swallow
}
