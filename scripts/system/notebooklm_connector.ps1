param(
    [ValidateSet("profile", "resolve-notebook", "create-notebook", "add-source-url", "seed-notebooks", "ingest-report", "agent-dual")]
    [string]$Action = "profile",
    [string]$Session = "1",
    [string]$WorkspaceUrl = "https://notebooklm.google.com/",
    [string]$NotebookUrl = "",
    [string]$NotebookId = "",
    [string]$Title = "",
    [string]$Prompt = "",
    [string[]]$SourceUrl = @(),
    [string]$SourceUrlFile = "",
    [string[]]$ReportFile = @(),
    [int]$Count = 1,
    [string]$NamePrefix = "SCBE Research Notebook",
    [int]$TimeoutMs = 30000,
    [int]$VisualPreviewChars = 1800,
    [string]$RegistryPath = "",
    [switch]$NoReuseExisting,
    [switch]$NoDedupeSources,
    [string]$Output = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "notebooklm_connector.py"
if (-not (Test-Path $scriptPath)) {
    throw "Missing connector script: $scriptPath"
}

$argsList = @(
    $scriptPath,
    "--action", $Action,
    "--session", $Session,
    "--workspace-url", $WorkspaceUrl,
    "--count", "$Count",
    "--name-prefix", $NamePrefix,
    "--timeout-ms", "$TimeoutMs",
    "--visual-preview-chars", "$VisualPreviewChars"
)

if (-not [string]::IsNullOrWhiteSpace($NotebookUrl)) { $argsList += @("--notebook-url", $NotebookUrl) }
if (-not [string]::IsNullOrWhiteSpace($NotebookId)) { $argsList += @("--notebook-id", $NotebookId) }
if (-not [string]::IsNullOrWhiteSpace($Title)) { $argsList += @("--title", $Title) }
if (-not [string]::IsNullOrWhiteSpace($Prompt)) { $argsList += @("--prompt", $Prompt) }
if (-not [string]::IsNullOrWhiteSpace($SourceUrlFile)) { $argsList += @("--source-url-file", $SourceUrlFile) }
if (-not [string]::IsNullOrWhiteSpace($Output)) { $argsList += @("--output", $Output) }
if (-not [string]::IsNullOrWhiteSpace($RegistryPath)) { $argsList += @("--registry-path", $RegistryPath) }
if ($DryRun) { $argsList += "--dry-run" }
if ($NoReuseExisting) { $argsList += "--no-reuse-existing" }
if ($NoDedupeSources) { $argsList += "--no-dedupe-sources" }
foreach ($url in $SourceUrl) {
    if (-not [string]::IsNullOrWhiteSpace($url)) {
        $argsList += @("--source-url", $url)
    }
}
foreach ($rf in $ReportFile) {
    if (-not [string]::IsNullOrWhiteSpace($rf)) {
        $argsList += @("--report-file", $rf)
    }
}

python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "NotebookLM connector failed with exit code $LASTEXITCODE"
}
