param(
    [string]$OutputRoot = "artifacts/releases"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stageDir = Join-Path $repoRoot "dist\aethercode-browser-$timestamp"
$releaseRoot = Join-Path $repoRoot $OutputRoot
$zipPath = Join-Path $releaseRoot "aethercode-browser-$timestamp.zip"

if (Test-Path $stageDir) {
    Remove-Item -Recurse -Force $stageDir
}
New-Item -ItemType Directory -Path $stageDir | Out-Null
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

$files = @(
    "src/aethercode/app.html",
    "src/aethercode/arena.html",
    "src/aethercode/gateway.py",
    "src/aethercode/manifest.json",
    "src/aethercode/sw.js",
    "src/aethercode/static/icons/icon-192.png",
    "src/aethercode/static/icons/icon-512.png",
    "scripts/start_kerrigan.ps1"
)

foreach ($rel in $files) {
    $src = Join-Path $repoRoot $rel
    if (-not (Test-Path $src)) {
        Write-Warning "Skipping missing file: $rel"
        continue
    }
    $dst = Join-Path $stageDir $rel
    $dstDir = Split-Path -Parent $dst
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    Copy-Item -Path $src -Destination $dst -Force
}

$runScript = @'
Set-Location $PSScriptRoot
Set-Location ..
python -m uvicorn src.aethercode.gateway:app --host 127.0.0.1 --port 8500
'@
$runPath = Join-Path $stageDir "RUN_AETHERCODE.ps1"
$runScript | Set-Content -Path $runPath -Encoding UTF8

$readme = @'
AetherCode Browser Package
==========================

1) Install Python 3.10+.
2) From this folder run:
   powershell -ExecutionPolicy Bypass -File .\RUN_AETHERCODE.ps1
3) Open:
   http://127.0.0.1:8500/
4) In browser choose Install App (or Add to Home Screen on mobile).

Includes:
- Installable PWA manifest + service worker
- Main app UI (/)
- Arena UI (/arena)
- Gateway API backend
'@
$readmePath = Join-Path $stageDir "README_INSTALL.txt"
$readme | Set-Content -Path $readmePath -Encoding UTF8

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}
Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Output "Staged: $stageDir"
Write-Output "Zip:    $zipPath"
