param(
    [string]$VenvPath = ".venv-garak",
    [string]$OutputDir = "artifacts\benchmark\garak_smoke",
    [string]$TargetType = "test.Blank",
    [string]$Probes = "test.Test",
    [string]$ReportPrefix = "scbe_garak_smoke"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
    $venvPython = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        throw "Garak venv not found at $VenvPath. Run scripts/benchmark/setup_garak_venv.ps1 first."
    }

    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    & $venvPython -m garak --target_type $TargetType --probes $Probes --report_prefix $ReportPrefix
    if ($LASTEXITCODE -ne 0) {
        throw "garak smoke run failed with exit code $LASTEXITCODE"
    }

    $garakRuns = Join-Path $HOME ".local\share\garak\garak_runs"
    Get-ChildItem -Path $garakRuns -Filter "$ReportPrefix*" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 5 |
        ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $OutputDir -Force }
} finally {
    Pop-Location
}
