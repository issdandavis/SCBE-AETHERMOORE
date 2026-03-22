param(
    [string]$RepoRoot = (Get-Location).Path,
    [string]$Branch = "",
    [ValidateSet("targeted", "core", "full")]
    [string]$Mode = "core",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    param([string]$Start)

    $current = [System.IO.Path]::GetFullPath($Start)
    while ($true) {
        if (Test-Path (Join-Path $current ".git")) {
            return $current
        }

        $parent = Split-Path $current -Parent
        if (-not $parent -or $parent -eq $current) {
            throw "Could not locate repo root from '$Start'."
        }
        $current = $parent
    }
}

function Invoke-Step {
    param(
        [string]$Label,
        [string]$WorkingDirectory,
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    Write-Host ""
    Write-Host "==> $Label" -ForegroundColor Cyan
    Write-Host "$FilePath $($ArgumentList -join ' ')" -ForegroundColor DarkGray

    if ($DryRun) {
        return
    }

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -NoNewWindow `
        -Wait `
        -PassThru

    if ($process.ExitCode -ne 0) {
        throw "Step failed: $Label (exit code $($process.ExitCode))"
    }
}

$resolvedRepo = Resolve-RepoRoot -Start $RepoRoot
$branchValidation = Join-Path $resolvedRepo "scripts\\branch_validation.ps1"

if (-not $Branch) {
    Push-Location $resolvedRepo
    try {
        $Branch = (git branch --show-current).Trim()
    }
    finally {
        Pop-Location
    }
}

if ($Mode -eq "targeted") {
    Write-Host "Targeted mode does not guess commands." -ForegroundColor Yellow
    Write-Host "Run file-specific pytest/vitest/typecheck based on the current diff." -ForegroundColor Yellow
    exit 0
}

if (Test-Path $branchValidation) {
    $args = @("-File", $branchValidation, "-Branch", $Branch, "-Profile", $Mode)
    if ($DryRun) {
        $args += "-DryRun"
    }
    Invoke-Step -Label "branch-validation-$Mode" -WorkingDirectory $resolvedRepo -FilePath "pwsh" -ArgumentList $args
    exit 0
}

Invoke-Step -Label "root-typecheck" -WorkingDirectory $resolvedRepo -FilePath "npm" -ArgumentList @("run", "typecheck")
Invoke-Step -Label "root-vitest" -WorkingDirectory $resolvedRepo -FilePath "npm" -ArgumentList @("test")
Invoke-Step -Label "root-release-preflight" -WorkingDirectory $resolvedRepo -FilePath "python" -ArgumentList @("run_tests.py", "release", "--preflight")
