param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$OpenClawSkillsDir = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

if ([string]::IsNullOrWhiteSpace($OpenClawSkillsDir)) {
    $OpenClawSkillsDir = Join-Path $env:USERPROFILE ".openclaw\skills"
}

$sourceRoot = Join-Path $RepoRoot "external\openclaw\skills"
$skillNames = @(
    "scbe-hydra-armor",
    "scbe-internet-navigation-lanes",
    "scbe-hydra-clawbot-synthesis"
)

New-Item -ItemType Directory -Force -Path $OpenClawSkillsDir | Out-Null

$installed = @()
foreach ($name in $skillNames) {
    $src = Join-Path $sourceRoot $name
    if (-not (Test-Path $src)) {
        throw "Missing source skill: $src"
    }

    $dst = Join-Path $OpenClawSkillsDir $name
    if ((Test-Path $dst) -and $Force) {
        Remove-Item -Recurse -Force $dst
    }
    if (-not (Test-Path $dst)) {
        New-Item -ItemType Directory -Force -Path $dst | Out-Null
    }

    Copy-Item -Path (Join-Path $src "*") -Destination $dst -Recurse -Force
    $installed += $dst
}

[pscustomobject]@{
    status = "ok"
    openclaw_skills_dir = $OpenClawSkillsDir
    installed = $installed
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 6
