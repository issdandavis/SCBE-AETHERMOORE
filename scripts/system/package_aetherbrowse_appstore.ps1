param(
  [ValidateSet("aab", "apk")]
  [string]$Format = "aab",
  [ValidateSet("play", "kindle")]
  [string]$Store = "play",
  [switch]$SkipInstall = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$kindleDir = Join-Path $repoRoot "kindle-app"

function Invoke-NpmChecked {
  param(
    [string]$Label,
    [string[]]$CommandArgs
  )
  & npm @CommandArgs
  if ($LASTEXITCODE -ne 0) {
    throw "$Label failed with exit code $LASTEXITCODE"
  }
}

if (-not (Test-Path $kindleDir)) {
  throw "kindle-app directory not found: $kindleDir"
}

if (-not $env:JAVA_HOME) {
  throw "JAVA_HOME is not set. Install JDK 17+ and set JAVA_HOME before packaging."
}

$javaExe = Join-Path $env:JAVA_HOME "bin\java.exe"
if (-not (Test-Path $javaExe)) {
  throw "JAVA_HOME is set but java.exe was not found at $javaExe"
}

Push-Location $kindleDir
try {
  if (-not $SkipInstall) {
    Write-Host "Installing kindle-app dependencies..." -ForegroundColor Cyan
    Invoke-NpmChecked -Label "npm install" -CommandArgs @("install")
  }

  $env:AETHERCODE_APP_VARIANT = "aetherbrowse"
  if ($Store -eq "kindle") {
    $env:AETHERCODE_TARGET = "kindle"
  } else {
    Remove-Item Env:\AETHERCODE_TARGET -ErrorAction SilentlyContinue
  }

  if ($Format -eq "aab") {
    if ($Store -eq "kindle") {
      Invoke-NpmChecked -Label "npm run build:aab:aetherbrowse:kindle" -CommandArgs @("run", "build:aab:aetherbrowse:kindle")
    } else {
      Invoke-NpmChecked -Label "npm run build:aab:aetherbrowse" -CommandArgs @("run", "build:aab:aetherbrowse")
    }
    $sourceFile = Join-Path $kindleDir "android\app\build\outputs\bundle\release\app-release.aab"
  } else {
    if ($Store -eq "kindle") {
      Invoke-NpmChecked -Label "npm run build:apk:aetherbrowse:kindle" -CommandArgs @("run", "build:apk:aetherbrowse:kindle")
    } else {
      Invoke-NpmChecked -Label "npm run build:apk:aetherbrowse" -CommandArgs @("run", "build:apk:aetherbrowse")
    }
    $sourceFile = Join-Path $kindleDir "android\app\build\outputs\apk\release\app-release.apk"
  }

  if (-not (Test-Path $sourceFile)) {
    throw "Build completed but artifact not found at $sourceFile"
  }

  $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
  $releaseDir = Join-Path $repoRoot ("artifacts\releases\aetherbrowse-appstore\" + $stamp)
  New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

  $ext = [System.IO.Path]::GetExtension($sourceFile)
  $targetArtifact = Join-Path $releaseDir ("aetherbrowse-" + $Store + $ext)
  Copy-Item -Path $sourceFile -Destination $targetArtifact -Force

  $listingSource = Join-Path $kindleDir "store-listing-aetherbrowse.md"
  if (Test-Path $listingSource) {
    Copy-Item -Path $listingSource -Destination (Join-Path $releaseDir "store-listing-aetherbrowse.md") -Force
  }

  $artifactHash = (Get-FileHash -Path $targetArtifact -Algorithm SHA256).Hash
  $manifest = [ordered]@{
    packaged_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    app = "AetherBrowse"
    app_id = "com.issdandavis.aetherbrowse"
    store_target = $Store
    format = $Format
    artifact_path = $targetArtifact
    artifact_sha256 = $artifactHash
    source_path = $sourceFile
    release_dir = $releaseDir
  }
  $manifestPath = Join-Path $releaseDir "release_manifest.json"
  $manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8

  Write-Host "AetherBrowse package ready." -ForegroundColor Green
  Write-Host "Artifact: $targetArtifact" -ForegroundColor Gray
  Write-Host "Manifest: $manifestPath" -ForegroundColor Gray
} finally {
  Pop-Location
}
