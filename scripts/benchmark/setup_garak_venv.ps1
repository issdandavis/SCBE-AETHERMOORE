param(
    [string]$Python = "py",
    [string[]]$PythonArgs = @("-3.12"),
    [string]$VenvPath = ".venv-garak",
    [switch]$UseUvFallback
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
    if (-not (Test-Path $VenvPath)) {
        & $Python @PythonArgs -m venv $VenvPath
        if ($LASTEXITCODE -ne 0 -and $UseUvFallback) {
            Write-Host "Python launcher venv creation failed; trying uv-managed Python 3.12..."
            & uv python install 3.12
            if ($LASTEXITCODE -ne 0) {
                throw "uv python install 3.12 failed with exit code $LASTEXITCODE"
            }
            & uv venv --python 3.12 $VenvPath
        }
        if ($LASTEXITCODE -ne 0) {
            throw "venv creation failed with exit code $LASTEXITCODE. Try -UseUvFallback or install Python 3.12."
        }
    }

    $venvPython = Join-Path $VenvPath "Scripts\python.exe"
    & $venvPython -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ensurepip unavailable; using uv pip for package installation."
    }

    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        & uv pip install --python $venvPython pip
        if ($LASTEXITCODE -ne 0) {
            throw "pip bootstrap failed with exit code $LASTEXITCODE"
        }
    }

    & $venvPython -m pip install "garak==0.14.1"
    if ($LASTEXITCODE -ne 0) {
        throw "garak install failed with exit code $LASTEXITCODE"
    }

    & $venvPython -m garak --version
} finally {
    Pop-Location
}
