param(
    [string]$OutputRoot = "artifacts/releases",
    [switch]$SkipAssetCopy
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$kindleRoot = Join-Path $repoRoot "kindle-app"
$wwwRoot = Join-Path $kindleRoot "www"
$outputDir = Join-Path $repoRoot $OutputRoot

if (-not (Test-Path $kindleRoot)) {
    throw "kindle-app directory not found: $kindleRoot"
}

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

if (-not $SkipAssetCopy) {
    Push-Location $kindleRoot
    try {
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            throw "npm not found. Install Node.js/npm first."
        }
        npm run copy:assets | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "npm run copy:assets failed."
        }
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path $wwwRoot)) {
    throw "PWA web root not found: $wwwRoot"
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipPath = Join-Path $outputDir ("aethercode-browser-{0}.zip" -f $timestamp)

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
}

Compress-Archive -Path (Join-Path $wwwRoot "*") -DestinationPath $zipPath -Force

$manifest = [ordered]@{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    profile = "pwa-download"
    source = $wwwRoot
    output_zip = $zipPath
}
$manifestPath = Join-Path $outputDir ("aethercode-browser-manifest-{0}.json" -f $timestamp)
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Output ("PWA ZIP: {0}" -f $zipPath)
Write-Output ("Manifest: {0}" -f $manifestPath)
