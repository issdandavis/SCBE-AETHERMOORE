[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Remove-StaleBuildArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $distPath = Join-Path $RepoRoot "dist"
    if (!(Test-Path $distPath)) {
        return
    }

    Write-Host ""
    Write-Host "==> Pre-clean stale build artifacts" -ForegroundColor Cyan

    $patterns = @("*.whl", "*.tar.gz")
    foreach ($pattern in $patterns) {
        Get-ChildItem -Path $distPath -Filter $pattern -Recurse -Force -ErrorAction SilentlyContinue |
            ForEach-Object {
                $item = $_
                try {
                    $item.Attributes = "Normal"
                    Remove-Item -Path $item.FullName -Force -ErrorAction Stop
                    Write-Host ("    removed: {0}" -f $item.FullName) -ForegroundColor DarkGray
                } catch {
                    Write-Warning ("Could not remove stale artifact: {0} ({1})" -f $item.FullName, $_.Exception.Message)
                }
            }
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    Write-Host ""
    Write-Host ("==> {0}" -f $Name) -ForegroundColor Cyan
    Write-Host ("    {0}" -f $Command) -ForegroundColor DarkGray

    & pwsh -NoProfile -Command $Command
    if ($LASTEXITCODE -ne 0) {
        throw ("Step failed: {0}" -f $Name)
    }
}

function Invoke-PreparePublishStep {
    Write-Host ""
    Write-Host "==> Prepare publish artifacts" -ForegroundColor Cyan
    Write-Host "    npm run publish:prepare" -ForegroundColor DarkGray

    & pwsh -NoProfile -Command "npm run publish:prepare"
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Warning "publish:prepare failed; attempting local fallback build path (dist/src only)."

    & pwsh -NoProfile -Command "npm run clean:release"
    if ($LASTEXITCODE -ne 0) {
        throw "Fallback failed at clean:release"
    }

    $distSrc = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "dist\\src"
    if (Test-Path $distSrc) {
        Remove-Item -Path $distSrc -Recurse -Force -ErrorAction SilentlyContinue
    }

    & pwsh -NoProfile -Command "npm run build:src"
    if ($LASTEXITCODE -ne 0) {
        throw "Fallback failed at build:src"
    }
}

Write-Host "SCBE release guard starting..." -ForegroundColor Green

Remove-StaleBuildArtifacts -RepoRoot (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Invoke-Step -Name "Install dependencies" -Command "npm ci"
Invoke-PreparePublishStep
Invoke-Step -Name "Run tests" -Command "npm test"
Invoke-Step -Name "Strict tarball guard" -Command "npm run publish:check:strict"

Write-Host ""
Write-Host "SCBE release guard passed." -ForegroundColor Green
