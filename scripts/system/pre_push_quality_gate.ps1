param(
    [switch]$SkipTests,
    [switch]$FullCli,
    [switch]$WaitForGithub,
    [string]$Remote = "origin",
    [string]$Branch = "",
    [int]$GithubTimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name"
    }
}

function Git-Output {
    param([string[]]$GitArgs)
    $out = & git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArgs -join ' ') failed"
    }
    return $out
}

$repoRoot = Git-Output @("rev-parse", "--show-toplevel")
Set-Location $repoRoot

if (-not $Branch) {
    $Branch = (Git-Output @("branch", "--show-current")).Trim()
}

Write-Host "SCBE pre-push quality gate" -ForegroundColor Green
Write-Host "repo:   $repoRoot"
Write-Host "branch: $Branch"
Write-Host "remote: $Remote"

Run-Step "git diff whitespace check" {
    git diff --check
}

Run-Step "changed-file inventory" {
    git status --short
}

Run-Step "JavaScript syntax checks" {
    node --check packages/cli/bin/scbe.js
    node --check packages/cli/scripts/bench_task_corpus.cjs
    node --check packages/cli/scripts/bench_harness_matrix.cjs
}

Run-Step "Prettier check for CLI benchmark surface" {
    npx prettier --check `
        packages/cli/bin/scbe.js `
        packages/cli/scripts/bench_task_corpus.cjs `
        packages/cli/scripts/bench_harness_matrix.cjs `
        packages/cli/scripts/shell_benchmark.cjs `
        packages/cli/tests/bench.test.cjs `
        packages/cli/tests/shell.test.cjs `
        config/eval/external_codegen_eval_tasks.sample.json `
        config/eval/hard_benchmark_targets.v1.json
}

if (-not $SkipTests) {
    if ($FullCli) {
        Run-Step "full CLI tests" {
            npm --prefix packages/cli test
        }
    } else {
        Run-Step "targeted benchmark and shell tests" {
            node --test packages/cli/tests/bench.test.cjs --test-name-pattern "task corpus"
            node --test packages/cli/tests/shell.test.cjs --test-name-pattern "trap-dispatch normalizes"
        }
    }
}

Run-Step "harness matrix smoke" {
    node packages/cli/scripts/bench_harness_matrix.cjs
}

Write-Host ""
Write-Host "Local gate passed. Safe next command:" -ForegroundColor Green
Write-Host "  git push $Remote $Branch"

if ($WaitForGithub) {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "GitHub wait requested, but gh is not installed or not on PATH"
    }
    Write-Host ""
    Write-Host "Waiting for latest GitHub Actions run on $Branch..." -ForegroundColor Cyan
    $deadline = (Get-Date).AddSeconds($GithubTimeoutSeconds)
    do {
        $json = gh run list --branch $Branch --limit 1 --json databaseId,status,conclusion,displayTitle,workflowName,createdAt 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $json) {
            Start-Sleep -Seconds 10
            continue
        }
        $run = $json | ConvertFrom-Json | Select-Object -First 1
        if ($run) {
            Write-Host ("run {0}: {1} / {2} - {3}" -f $run.databaseId, $run.status, $run.conclusion, $run.workflowName)
            if ($run.status -eq "completed") {
                if ($run.conclusion -eq "success") {
                    Write-Host "GitHub check passed." -ForegroundColor Green
                    exit 0
                }
                throw "GitHub check completed with conclusion: $($run.conclusion)"
            }
        }
        Start-Sleep -Seconds 15
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for GitHub Actions after $GithubTimeoutSeconds seconds"
}
