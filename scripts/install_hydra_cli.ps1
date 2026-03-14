param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$InstallDir = (Join-Path $HOME ".scbe\bin"),
    [switch]$NoPathUpdate
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python not found in PATH"
}

$hydraMain = Join-Path $RepoRoot "hydra\__main__.py"
if (-not (Test-Path $hydraMain)) {
    throw "HYDRA package not found at $hydraMain"
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$repoForPs = $RepoRoot.Replace("'", "''")
$repoForCmd = $RepoRoot.Replace('"', '""')

$psShim = @"
param(
    [Parameter(ValueFromRemainingArguments = `$true)]
    [string[]]`$Args
)

`$repoRoot = '$repoForPs'
`$env:PYTHONPATH = "`$repoRoot;`$repoRoot\src;`$env:PYTHONPATH"
& python -m hydra @Args
exit `$LASTEXITCODE
"@

$cmdShim = @"
@echo off
setlocal
set "REPO_ROOT=$repoForCmd"
set "PYTHONPATH=%REPO_ROOT%;%REPO_ROOT%\src;%PYTHONPATH%"
python -m hydra %*
exit /b %ERRORLEVEL%
"@

$psShimPath = Join-Path $InstallDir "hydra.ps1"
$cmdShimPath = Join-Path $InstallDir "hydra.cmd"

Set-Content -Path $psShimPath -Value $psShim -Encoding UTF8
Set-Content -Path $cmdShimPath -Value $cmdShim -Encoding ASCII

$pathUpdated = $false
if (-not $NoPathUpdate) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ([string]::IsNullOrWhiteSpace($userPath)) {
        [Environment]::SetEnvironmentVariable("Path", $InstallDir, "User")
        $pathUpdated = $true
    }
    elseif (-not (($userPath -split ";") -contains $InstallDir)) {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$InstallDir", "User")
        $pathUpdated = $true
    }
}

if (-not (($env:Path -split ";") -contains $InstallDir)) {
    $env:Path = "$InstallDir;$env:Path"
}

Write-Host "Installed HYDRA shims:"
Write-Host "  $psShimPath"
Write-Host "  $cmdShimPath"
if ($pathUpdated) {
    Write-Host "User PATH updated. Open a new terminal to use 'hydra' globally."
}
else {
    Write-Host "PATH already contained install dir or --NoPathUpdate was used."
}
Write-Host "Quick test:"
Write-Host "  hydra --help"
