param(
    [string]$Python = ".venv-garak\Scripts\python.exe",
    [switch]$IncludeProtectAI,
    [int]$MaxRows = 0
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
    if (-not (Test-Path $Python)) {
        throw "Python not found at $Python. Run scripts/benchmark/setup_garak_venv.ps1 -UseUvFallback first."
    }

    $args = @("scripts/benchmark/third_party_prompt_injection_matrix.py")
    if ($IncludeProtectAI) {
        $args += "--include-protectai"
    }
    if ($MaxRows -gt 0) {
        $args += @("--max-rows", "$MaxRows")
    }

    & $Python @args
    if ($LASTEXITCODE -ne 0) {
        throw "third-party matrix failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
