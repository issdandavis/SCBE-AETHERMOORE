param(
    [string]$OutputRoot = "artifacts/benchmark/latest"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$resolvedOutput = Join-Path $repoRoot $OutputRoot

New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null

Write-Host "SCBE eval pack runner"
Write-Host "Repo root: $repoRoot"
Write-Host "Output:    $resolvedOutput"

Push-Location $repoRoot
try {
    $commands = @(
        @{
            Name = "corpus_benchmark"
            Command = "pytest tests/adversarial/test_adversarial_benchmark.py -v"
        },
        @{
            Name = "industry_compare"
            Command = "python scripts/benchmark/scbe_vs_industry.py"
        }
    )

    $results = @()
    foreach ($step in $commands) {
        Write-Host ""
        Write-Host "Running: $($step.Command)"
        & powershell -NoProfile -Command $step.Command
        $results += [pscustomobject]@{
            name = $step.Name
            command = $step.Command
            status = "completed"
            finished_at = (Get-Date).ToUniversalTime().ToString("o")
        }
    }

    $summary = [pscustomobject]@{
        eval_id = "scbe-public-adversarial-pack"
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        repo_root = $repoRoot
        output_root = $resolvedOutput
        steps = $results
        expected_artifacts = @(
            "artifacts/benchmark/industry_benchmark_report.json"
        )
    }

    $summary | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $resolvedOutput "eval_summary.json")
    Write-Host ""
    Write-Host "Eval summary written to $(Join-Path $resolvedOutput "eval_summary.json")"
}
finally {
    Pop-Location
}
