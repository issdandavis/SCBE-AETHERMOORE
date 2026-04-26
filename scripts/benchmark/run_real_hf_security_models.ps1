param(
    [switch]$RequireExternalModels,
    [string]$Lanes = "protectai,meta_prompt_guard",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
    $env:SCBE_BENCHMARK_USE_EXTERNAL_MODELS = "1"
    $env:SCBE_BENCHMARK_EXTERNAL_LANES = $Lanes
    if ($RequireExternalModels) {
        $env:SCBE_BENCHMARK_REQUIRE_EXTERNAL_MODELS = "1"
    } else {
        Remove-Item Env:\SCBE_BENCHMARK_REQUIRE_EXTERNAL_MODELS -ErrorAction SilentlyContinue
    }

    & $Python scripts/benchmark/scbe_vs_industry.py
    if ($LASTEXITCODE -ne 0) {
        throw "scbe_vs_industry.py failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
