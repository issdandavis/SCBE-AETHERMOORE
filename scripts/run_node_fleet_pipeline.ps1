param(
    [string[]]$DocsGlob = @(),
    [int]$Epochs = 20,
    [string]$ModelRepo = "issdandavis/phdm-21d-embedding",
    [string]$ConversationSpinGist = "c38b2eface8d456b90c6bf02678871d8",
    [bool]$PushToHub = $true,
    [bool]$GenerateNews = $true
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$extraGlobs = @()

if ($DocsGlob.Count -gt 0) {
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $ingestOut = "training/ingest/docs_$stamp.jsonl"
    $ingestCmd = @("python", "scripts/ingest_docs_to_training_jsonl.py", "--out", $ingestOut)
    foreach ($g in $DocsGlob) {
        $ingestCmd += @("--glob", $g)
    }
    & $ingestCmd[0] $ingestCmd[1..($ingestCmd.Count - 1)]
    $extraGlobs += $ingestOut
}

$trainCmd = @(
    "python", "training/train_node_fleet_three_specialty.py",
    "--epochs", "$Epochs",
    "--conversation-spin-gist", "$ConversationSpinGist",
    "--model-repo", "$ModelRepo"
)

if ($PushToHub) {
    $trainCmd += "--push-to-hub"
}
foreach ($g in $extraGlobs) {
    $trainCmd += @("--local-glob", $g)
}

$trainOutput = & $trainCmd[0] $trainCmd[1..($trainCmd.Count - 1)] 2>&1
$trainOutput | ForEach-Object { $_ }

$runMatch = $trainOutput | Select-String -Pattern "^Run dir:\s*(.+)$" | Select-Object -Last 1
if (-not $runMatch) {
    throw "Could not parse run directory from training output."
}
$runDir = $runMatch.Matches[0].Groups[1].Value.Trim()

if ($GenerateNews) {
    python scripts/generate_node_fleet_news.py --run-dir $runDir
}

Write-Host ""
Write-Host "Pipeline complete."
Write-Host "RunDir: $runDir"
if ($GenerateNews) {
    Write-Host "News: docs/news/latest.md"
}
