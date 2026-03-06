param(
    [Parameter(Mandatory = $true)]
    [string]$Url,
    [string]$TaskId = "",
    [string]$Summary = "Playwright extension run",
    [string]$Sender = "agent.codex",
    [string]$Recipient = "agent.claude",
    [string]$Intent = "handoff",
    [string]$OutputDir = "artifacts/playwright_extension",
    [ValidateSet("auto", "playwright", "http")]
    [string]$Engine = "playwright",
    [switch]$SkipCrossTalk,
    [switch]$SkipNodeBrowse
)

$scriptPath = Join-Path $PSScriptRoot "playwright_extension_runner.py"
if (-not (Test-Path $scriptPath)) {
    Write-Error "Runner not found: $scriptPath"
    exit 1
}

$argsList = @(
    $scriptPath,
    "--url", $Url,
    "--summary", $Summary,
    "--sender", $Sender,
    "--recipient", $Recipient,
    "--intent", $Intent,
    "--output-dir", $OutputDir,
    "--engine", $Engine
)

if ($TaskId) {
    $argsList += @("--task-id", $TaskId)
}
if ($SkipCrossTalk) {
    $argsList += "--skip-crosstalk"
}
if ($SkipNodeBrowse) {
    $argsList += "--skip-node-browse"
}

python @argsList
exit $LASTEXITCODE
