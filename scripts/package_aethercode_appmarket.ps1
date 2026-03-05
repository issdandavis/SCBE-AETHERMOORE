param(
    [string]$OutputRoot = "artifacts/releases",
    [switch]$SkipPwa,
    [switch]$SkipDesktop,
    [switch]$InstallDeps,
    [int]$BuildRetries = 3
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$outputDir = Join-Path $repoRoot $OutputRoot
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$pwaZip = $null
$desktopArtifacts = @()

if (-not $SkipPwa) {
    $pwaScript = Join-Path $repoRoot "scripts/package_aethercode_download.ps1"
    if (-not (Test-Path $pwaScript)) {
        throw "Missing PWA packager: $pwaScript"
    }
    & $pwaScript -OutputRoot $OutputRoot
    $pwaZip = Get-ChildItem -Path $outputDir -Filter "aethercode-browser-*.zip" |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
}

if (-not $SkipDesktop) {
    $desktopRoot = Join-Path $repoRoot "aetherbrowse"
    if (-not (Test-Path (Join-Path $desktopRoot "package.json"))) {
        throw "Missing desktop app package.json at $desktopRoot"
    }

    Push-Location $desktopRoot
    try {
        if ($InstallDeps -or -not (Test-Path (Join-Path $desktopRoot "node_modules"))) {
            npm install
            if ($LASTEXITCODE -ne 0) {
                throw "npm install failed in $desktopRoot"
            }
        }

        $buildOk = $false
        for ($attempt = 1; $attempt -le [Math]::Max(1, $BuildRetries); $attempt++) {
            Write-Output ("Desktop build attempt {0}/{1}" -f $attempt, [Math]::Max(1, $BuildRetries))
            npm run build:win
            if ($LASTEXITCODE -eq 0) {
                $buildOk = $true
                break
            }
            if ($attempt -lt [Math]::Max(1, $BuildRetries)) {
                Start-Sleep -Seconds (8 * $attempt)
            }
        }
        if (-not $buildOk) {
            throw "npm run build:win failed in $desktopRoot after $BuildRetries attempt(s)"
        }
    }
    finally {
        Pop-Location
    }

    $desktopOut = Join-Path $repoRoot "artifacts/releases/aetherbrowse-desktop"
    if (Test-Path $desktopOut) {
        $desktopArtifacts = Get-ChildItem -Path $desktopOut -File |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object Name, FullName, Length, LastWriteTimeUtc
    }
}

$manifest = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    profile = "appmarket"
    output_root = (Resolve-Path $outputDir).Path
    pwa_zip = if ($pwaZip) { $pwaZip.FullName } else { "" }
    desktop_artifacts = @($desktopArtifacts | ForEach-Object {
            [ordered]@{
                name = $_.Name
                path = $_.FullName
                bytes = $_.Length
                modified_utc = $_.LastWriteTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
            }
        })
}

$manifestPath = Join-Path $outputDir ("aethercode-appmarket-manifest-{0}.json" -f $timestamp)
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Output "App-market packaging complete."
if ($pwaZip) {
    Write-Output ("PWA ZIP: {0}" -f $pwaZip.FullName)
}
if ($desktopArtifacts.Count -gt 0) {
    Write-Output ("Desktop artifacts: {0}" -f $desktopArtifacts.Count)
}
Write-Output ("Manifest: {0}" -f $manifestPath)
