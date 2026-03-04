[CmdletBinding()]
param(
    [string[]]$Topics = @(),
    [string]$UrlsFile = "",
    [ValidateSet("playwright", "selenium", "chrome_mcp", "cdp")]
    [string]$Backend = "playwright",
    [int]$MaxTabs = 8,
    [int]$MaxPerTopic = 8,
    [string]$Query = "headless first deep research spine",
    [string]$ObsidianRoot = "C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder",
    [switch]$SkipCoreCheck
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pipelineScript = Join-Path $repoRoot "scripts\web_research_training_pipeline.py"

if (-not $Topics -or $Topics.Count -eq 0) {
    $Topics = @(
        "site:arxiv.org AI governance research",
        "site:.gov AI policy standards",
        "niche autonomous systems safety",
        "machine science browser automation evidence"
    )
}

if ([string]::IsNullOrWhiteSpace($UrlsFile)) {
    $topicsDir = Join-Path $repoRoot "training\topics"
    New-Item -ItemType Directory -Path $topicsDir -Force | Out-Null
    $UrlsFile = Join-Path $topicsDir "headless_spine_seed_urls.json"
    $seedUrls = @(
        "https://arxiv.org",
        "https://scholar.google.com",
        "https://www.nist.gov",
        "https://www.darpa.mil",
        "https://www.nasa.gov",
        "https://www.uspto.gov",
        "https://www.cisa.gov",
        "https://www.energy.gov",
        "https://www.noaa.gov",
        "https://www.fda.gov"
    )
    $seedUrls | ConvertTo-Json | Set-Content -Path $UrlsFile -Encoding utf8
}

$argv = @(
    $pipelineScript,
    "--backend", $Backend,
    "--max-tabs", "$MaxTabs",
    "--max-per-topic", "$MaxPerTopic",
    "--query", $Query,
    "--urls-file", $UrlsFile,
    "--obsidian-root", $ObsidianRoot,
    "--topics"
) + $Topics

if ($SkipCoreCheck) {
    $argv += "--skip-core-check"
}

Write-Host "Running headless research spine pipeline..." -ForegroundColor Cyan
Write-Host ("python " + ($argv -join " ")) -ForegroundColor DarkGray

python @argv
$exitCode = $LASTEXITCODE

# The pipeline uses exit code 2 for governance quarantine outcomes.
if ($exitCode -eq 0 -or $exitCode -eq 2) {
    exit 0
}
exit $exitCode
