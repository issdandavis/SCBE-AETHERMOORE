param(
    [string]$CodexHome = "$HOME/.codex"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $repoRoot "skills/scbe-playwright-ops-extension"
$target = Join-Path $CodexHome "skills/scbe-playwright-ops-extension"

if (-not (Test-Path $source)) {
    throw "Source skill path not found: $source"
}

if (Test-Path $target) {
    Remove-Item -Recurse -Force $target
}
New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
Copy-Item -Recurse -Force $source $target
Write-Host "Installed skill to: $target"
