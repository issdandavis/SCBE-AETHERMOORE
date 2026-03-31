param(
    [string]$ConfigPath = "config/training/training_data_homebase.json",
    [string[]]$DraftRoot = @(),
    [string[]]$ClaudeExportZip = @(),
    [string[]]$ExcludeGlob = @(),
    [switch]$Commit,
    [switch]$Push,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))

function Resolve-RepoPath {
    param([string]$RawPath)
    if ([string]::IsNullOrWhiteSpace($RawPath)) {
        return $null
    }
    if ([System.IO.Path]::IsPathRooted($RawPath)) {
        return [System.IO.Path]::GetFullPath($RawPath)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $RawPath))
}

function Add-UniquePath {
    param(
        [System.Collections.Generic.List[string]]$Target,
        [System.Collections.Generic.HashSet[string]]$Seen,
        [string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }
    if ($Seen.Add($Value)) {
        $Target.Add($Value) | Out-Null
    }
}

function Resolve-GlobEntries {
    param([string]$Pattern)
    $resolved = @()
    if ([string]::IsNullOrWhiteSpace($Pattern)) {
        return $resolved
    }
    if ($Pattern.IndexOfAny([char[]]@('*', '?', '[')) -ge 0) {
        $resolved = @(Get-ChildItem -Path $Pattern -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTimeUtc -Descending |
                ForEach-Object { $_.FullName })
    }
    else {
        $candidate = Resolve-RepoPath $Pattern
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            $resolved = @($candidate)
        }
    }
    return $resolved
}

$configFile = Resolve-RepoPath $ConfigPath
if (-not (Test-Path -LiteralPath $configFile)) {
    throw "Config file not found: $configFile"
}

$config = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json

$draftRoots = [System.Collections.Generic.List[string]]::new()
$draftSeen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($item in @($config.draft_roots) + $DraftRoot) {
    $candidate = Resolve-RepoPath $item
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
        Add-UniquePath -Target $draftRoots -Seen $draftSeen -Value $candidate
    }
}

$claudeExports = [System.Collections.Generic.List[string]]::new()
$claudeSeen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($item in @($config.claude_export_globs) + $ClaudeExportZip) {
    foreach ($resolved in Resolve-GlobEntries $item) {
        Add-UniquePath -Target $claudeExports -Seen $claudeSeen -Value $resolved
    }
}

$excludeGlobs = [System.Collections.Generic.List[string]]::new()
$excludeSeen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($item in @($config.exclude_globs) + $ExcludeGlob) {
    if (-not [string]::IsNullOrWhiteSpace($item)) {
        Add-UniquePath -Target $excludeGlobs -Seen $excludeSeen -Value $item
    }
}

$extraInputs = [System.Collections.Generic.List[string]]::new()
$extraSeen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($item in @($config.extra_inputs)) {
    $candidate = Resolve-RepoPath $item
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
        Add-UniquePath -Target $extraInputs -Seen $extraSeen -Value $candidate
    }
}

$pythonArgs = [System.Collections.Generic.List[string]]::new()
$pythonArgs.Add("scripts/system/publish_training_dataset_repo.py") | Out-Null
if ($config.include_training_data) {
    $pythonArgs.Add("--include-training-data") | Out-Null
}
foreach ($zip in $claudeExports) {
    $pythonArgs.Add("--claude-export-zip") | Out-Null
    $pythonArgs.Add($zip) | Out-Null
}
foreach ($root in $draftRoots) {
    $pythonArgs.Add("--draft-root") | Out-Null
    $pythonArgs.Add($root) | Out-Null
}
foreach ($inputPath in $extraInputs) {
    $pythonArgs.Add("--input") | Out-Null
    $pythonArgs.Add($inputPath) | Out-Null
}
foreach ($glob in $excludeGlobs) {
    $pythonArgs.Add("--exclude-glob") | Out-Null
    $pythonArgs.Add($glob) | Out-Null
}

$outputRepo = Resolve-RepoPath $config.output_repo
$pythonArgs.Add("--output-repo") | Out-Null
$pythonArgs.Add($outputRepo) | Out-Null
$pythonArgs.Add("--dataset-repo") | Out-Null
$pythonArgs.Add([string]$config.dataset_repo) | Out-Null

if ($Commit -or $Push) {
    $pythonArgs.Add("--git-commit") | Out-Null
}
if ($Push) {
    $pythonArgs.Add("--git-push") | Out-Null
}

$resolvedSummary = [ordered]@{
    config = $configFile
    dataset_repo = [string]$config.dataset_repo
    output_repo = $outputRepo
    include_training_data = [bool]$config.include_training_data
    claude_export_zips = @($claudeExports)
    draft_roots = @($draftRoots)
    extra_inputs = @($extraInputs)
    exclude_globs = @($excludeGlobs)
    commit = [bool]$Commit
    push = [bool]$Push
}

if ($DryRun) {
    $resolvedSummary["python_command"] = @("python") + @($pythonArgs)
    $resolvedSummary | ConvertTo-Json -Depth 6
    exit 0
}

Write-Host "Publishing training data from repo control plane..." -ForegroundColor Cyan
$resolvedSummary | ConvertTo-Json -Depth 6 | Write-Host
& python @pythonArgs
