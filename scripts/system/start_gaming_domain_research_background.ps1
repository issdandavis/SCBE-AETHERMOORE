param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$TopicsFile = "training/topics/gaming_domains_topics.txt",
    [string]$UrlsFile = "training/topics/gaming_domains_seed_urls.json",
    [string]$Backend = "playwright",
    [int]$MaxPerTopic = 4,
    [int]$MaxTabs = 4,
    [string]$Query = "gaming market trends launch strategy monetization",
    [string]$N8nWebhook = "http://127.0.0.1:5680/webhook/scbe-notion-github-swarm",
    [switch]$SkipCoreCheck = $true,
    [switch]$RunBootstrap
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

if ($RunBootstrap) {
    $bootstrap = Join-Path $RepoRoot "scripts\system\bootstrap_24x7_local.ps1"
    if (Test-Path $bootstrap) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrap
    }
}

$jobRoot = Join-Path $RepoRoot "artifacts\background_jobs\gaming_domains"
New-Item -ItemType Directory -Force -Path $jobRoot | Out-Null

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$stdoutLog = Join-Path $jobRoot "$stamp.stdout.log"
$stderrLog = Join-Path $jobRoot "$stamp.stderr.log"
$metaPath = Join-Path $jobRoot "$stamp.meta.json"
$latestPath = Join-Path $jobRoot "latest.json"

$argsList = @(
    "scripts/web_research_training_pipeline.py",
    "--topics-file", $TopicsFile,
    "--max-per-topic", "$MaxPerTopic",
    "--backend", $Backend,
    "--max-tabs", "$MaxTabs",
    "--query", ('"{0}"' -f $Query.Replace('"', '\"'))
)

if (Test-Path $UrlsFile) {
    $argsList += @("--urls-file", $UrlsFile)
}
if ($SkipCoreCheck) {
    $argsList += "--skip-core-check"
}
if (-not [string]::IsNullOrWhiteSpace($N8nWebhook)) {
    $argsList += @("--n8n-webhook", $N8nWebhook)
}

$proc = Start-Process `
    -FilePath "python" `
    -ArgumentList $argsList `
    -WorkingDirectory $RepoRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

$meta = [ordered]@{
    started_utc = (Get-Date).ToUniversalTime().ToString("o")
    pid = $proc.Id
    status = "running"
    stdout_log = $stdoutLog
    stderr_log = $stderrLog
    command = @("python") + $argsList
    run_root = (Join-Path $RepoRoot "training\runs\web_research")
}

$meta | ConvertTo-Json -Depth 6 | Set-Content -Path $metaPath
$meta | ConvertTo-Json -Depth 6 | Set-Content -Path $latestPath
$meta | ConvertTo-Json -Depth 6
