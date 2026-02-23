param(
    [string]$RepoPath = "C:/Users/issda/SCBE-AETHERMOORE",
    [int]$TopN = 25,
    [string]$OutDir = "artifacts/system-audit"
)

$ErrorActionPreference = "Stop"

function Get-DirSizeBytes([string]$Path) {
    if (!(Test-Path $Path)) { return 0 }
    $sum = Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum
    return [int64]($sum.Sum)
}

function To-GB([int64]$bytes) {
    return [Math]::Round($bytes / 1GB, 3)
}

$repo = Resolve-Path $RepoPath
$outPath = Join-Path $repo $OutDir
New-Item -ItemType Directory -Force $outPath | Out-Null

$drive = Get-PSDrive -Name C
$topCandidates = @(
    "$repo/src",
    "$repo/docs",
    "$repo/tests",
    "$repo/node_modules",
    "$repo/.hypothesis",
    "$repo/.pytest_cache",
    "$repo/dist",
    "$repo/artifacts",
    "$repo/training",
    "$repo/training-data"
)

$rows = foreach ($p in $topCandidates) {
    [PSCustomObject]@{
        path = $p
        bytes = Get-DirSizeBytes $p
        gb = To-GB (Get-DirSizeBytes $p)
    }
}

$largestChildren = Get-ChildItem -LiteralPath $repo -Directory -Force -ErrorAction SilentlyContinue |
    ForEach-Object {
        $b = Get-DirSizeBytes $_.FullName
        [PSCustomObject]@{ name = $_.Name; path = $_.FullName; bytes = $b; gb = To-GB $b }
    } |
    Sort-Object bytes -Descending |
    Select-Object -First $TopN

$report = [PSCustomObject]@{
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    repo_path = "$repo"
    drive = [PSCustomObject]@{
        used_gb = [Math]::Round(($drive.Used / 1GB), 3)
        free_gb = [Math]::Round(($drive.Free / 1GB), 3)
    }
    targeted_paths = $rows
    largest_children = $largestChildren
}

$jsonFile = Join-Path $outPath "disk_audit.json"
$mdFile = Join-Path $outPath "disk_audit.md"
$report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $jsonFile

$md = @()
$md += "# Disk Audit"
$md += ""
$md += "- timestamp_utc: $($report.timestamp_utc)"
$md += "- repo_path: $($report.repo_path)"
$md += "- drive_used_gb: $($report.drive.used_gb)"
$md += "- drive_free_gb: $($report.drive.free_gb)"
$md += ""
$md += "## Targeted Paths"
$md += "| Path | GB |"
$md += "|---|---:|"
foreach ($r in $rows) { $md += "| $($r.path) | $($r.gb) |" }
$md += ""
$md += "## Largest Top-Level Folders"
$md += "| Name | GB |"
$md += "|---|---:|"
foreach ($r in $largestChildren) { $md += "| $($r.name) | $($r.gb) |" }
$md -join "`n" | Set-Content -Encoding UTF8 $mdFile

Write-Host "Wrote: $jsonFile"
Write-Host "Wrote: $mdFile"
