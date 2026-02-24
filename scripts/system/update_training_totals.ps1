param(
  [string]$RepoRoot = "",
  [string]$VaultRoot = "C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder",
  [string]$WorkspaceName = "AI Workspace",
  [string]$RoundTableRelative = "Round Table.md",
  [string]$SharedStateRelative = "Context\Shared State.md",
  [string]$ReportPath = "docs\map-room\training_totals_latest.md",
  [int]$TopN = 15,
  [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$trainingRoot = Join-Path $RepoRoot "training-data"
if (-not (Test-Path $trainingRoot)) {
  throw "training-data folder not found at: $trainingRoot"
}

$workspacePath = Join-Path $VaultRoot $WorkspaceName
$roundTablePath = Join-Path $workspacePath $RoundTableRelative
$sharedStatePath = Join-Path $workspacePath $SharedStateRelative
$reportFullPath = Join-Path $RepoRoot $ReportPath

$jsonlFiles = Get-ChildItem -Path $trainingRoot -Recurse -File -Filter *.jsonl
$rows = foreach ($f in $jsonlFiles) {
  $count = (Get-Content -Path $f.FullName | Measure-Object -Line).Lines
  [pscustomobject]@{
    FilePath = $f.FullName
    Relative = $f.FullName.Substring($RepoRoot.Length + 1)
    Pairs = [int]$count
    SizeKB = [math]::Round($f.Length / 1KB, 1)
  }
}

$totalPairs = ($rows | Measure-Object -Property Pairs -Sum).Sum
$totalFiles = ($rows | Measure-Object).Count
$topRows = $rows | Sort-Object Pairs -Descending | Select-Object -First $TopN
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$reportLines = @()
$reportLines += "# Training Totals Snapshot"
$reportLines += ""
$reportLines += "- generated_utc: $utc"
$reportLines += "- total_pairs: $totalPairs"
$reportLines += "- total_jsonl_files: $totalFiles"
$reportLines += ""
$reportLines += "## Top files"
$reportLines += ""
$reportLines += "| Pairs | Size (KB) | File |"
$reportLines += "|---:|---:|---|"
foreach ($row in $topRows) {
  $reportLines += "| $($row.Pairs) | $($row.SizeKB) | `$($row.Relative.Replace('\','/'))` |"
}
$reportLines += ""

if ($DryRun) {
  Write-Host "[dry-run] Would write report: $reportFullPath"
} else {
  New-Item -ItemType Directory -Force -Path (Split-Path $reportFullPath) | Out-Null
  $reportLines -join "`n" | Set-Content -Path $reportFullPath -Encoding UTF8
}

function Upsert-MarkerBlock {
  param(
    [string]$Path,
    [string]$StartMarker,
    [string]$EndMarker,
    [string[]]$BlockLines,
    [switch]$DryRunMode = $false
  )

  if (-not (Test-Path $Path)) {
    Write-Host "Skip (missing): $Path"
    return
  }

  $content = Get-Content -Path $Path -Raw
  $block = @($StartMarker) + $BlockLines + @($EndMarker)
  $replacement = ($block -join "`n") + "`n"

  $startEsc = [regex]::Escape($StartMarker)
  $endEsc = [regex]::Escape($EndMarker)
  $pattern = "(?s)$startEsc.*?$endEsc`r?`n?"

  if ([regex]::IsMatch($content, $pattern)) {
    $updated = [regex]::Replace($content, $pattern, $replacement)
  } else {
    if (-not $content.EndsWith("`n")) { $content += "`n" }
    $updated = $content + "`n" + $replacement
  }

  if ($DryRunMode) {
    Write-Host "[dry-run] Would update marker block in: $Path"
  } else {
    $updated | Set-Content -Path $Path -Encoding UTF8
    Write-Host "Updated: $Path"
  }
}

$blockLines = @(
  "## Training Totals Snapshot",
  "",
  "- updated_utc: $utc",
  "- total_pairs: **$totalPairs**",
  "- total_jsonl_files: **$totalFiles**",
  "- report: `$ReportPath`",
  "",
  "### Top $TopN files",
  "| Pairs | File |",
  "|---:|---|"
)
foreach ($row in $topRows) {
  $blockLines += "| $($row.Pairs) | `$($row.Relative.Replace('\','/'))` |"
}

Upsert-MarkerBlock `
  -Path $roundTablePath `
  -StartMarker "<!-- TRAINING_TOTALS_START -->" `
  -EndMarker "<!-- TRAINING_TOTALS_END -->" `
  -BlockLines $blockLines `
  -DryRunMode:$DryRun

Upsert-MarkerBlock `
  -Path $sharedStatePath `
  -StartMarker "<!-- TRAINING_TOTALS_START -->" `
  -EndMarker "<!-- TRAINING_TOTALS_END -->" `
  -BlockLines $blockLines `
  -DryRunMode:$DryRun

Write-Host ""
Write-Host "Training totals computed."
Write-Host "Pairs: $totalPairs"
Write-Host "JSONL files: $totalFiles"
Write-Host "Report: $reportFullPath"

