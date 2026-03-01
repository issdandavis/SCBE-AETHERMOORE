param(
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$OpenClawSourceDir = "C:\Users\issda\SCBE-AETHERMOORE\external\openclaw",
    [string]$OpenClawGitRepo = "https://github.com/openclaw/openclaw.git",
    [string]$OpenClawGitBranch = "main",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

if (-not $ProjectRoot -or -not (Test-Path $ProjectRoot)) {
    throw "ProjectRoot does not exist: $ProjectRoot"
}

if (-not $OpenClawSourceDir) {
    $OpenClawSourceDir = Join-Path $ProjectRoot "external\openclaw"
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git was not found. Install Git before using OpenClaw bootstrap."
}

$shouldClone = $false
if (-not (Test-Path $OpenClawSourceDir)) {
    $shouldClone = $true
} else {
    $hasCompose = Test-Path (Join-Path $OpenClawSourceDir "docker-compose.yml")
    $hasGit = Test-Path (Join-Path $OpenClawSourceDir ".git")
    if (-not $hasCompose -or -not $hasGit) {
        Write-Host "OpenClaw source folder exists but is incomplete: $OpenClawSourceDir"
        if ($Force) {
            Write-Host "Force flag set. Re-cloning OpenClaw source."
            Remove-Item -Recurse -Force $OpenClawSourceDir
            $shouldClone = $true
        } else {
            if (-not $hasCompose) {
                throw "OpenClaw folder is missing docker-compose.yml. Re-run with -Force to re-clone."
            }
            if (-not $hasGit) {
                Write-Host "OpenClaw folder is not a git checkout. Skipping fetch and using existing files."
            }
        }
    }
}

if ($shouldClone) {
    Write-Host "Cloning OpenClaw from upstream..."
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OpenClawSourceDir) | Out-Null
    & git clone --depth 1 --branch $OpenClawGitBranch $OpenClawGitRepo $OpenClawSourceDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to clone OpenClaw from $OpenClawGitRepo."
    }
}

if (Test-Path (Join-Path $OpenClawSourceDir ".git")) {
    Write-Host "OpenClaw git checkout found. Updating to latest $OpenClawGitBranch ..."
    & git -C $OpenClawSourceDir fetch --depth 1 origin $OpenClawGitBranch
    if ($LASTEXITCODE -eq 0) {
        & git -C $OpenClawSourceDir checkout $OpenClawGitBranch | Out-Null
        & git -C $OpenClawSourceDir reset --hard "origin/$OpenClawGitBranch" | Out-Null
    } else {
        Write-Host "WARN: OpenClaw fetch failed; using local checkout."
    }
}

if (-not (Test-Path (Join-Path $OpenClawSourceDir "docker-compose.yml"))) {
    throw "OpenClaw checkout is incomplete. Missing docker-compose.yml in: $OpenClawSourceDir"
}

$composePath = Join-Path $OpenClawSourceDir "docker-compose.yml"
$composePreview = Get-Content $composePath -TotalCount 12 -ErrorAction SilentlyContinue

[pscustomobject]@{
    status = "ready"
    openclaw_source_dir = $OpenClawSourceDir
    compose_file = $composePath
    git_repo = $OpenClawGitRepo
    git_branch = $OpenClawGitBranch
    has_compose = $true
    compose_preview = $composePreview -join "`n"
} | ConvertTo-Json -Depth 5
