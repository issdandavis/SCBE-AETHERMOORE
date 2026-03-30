param(
    [string]$Root = $env:USERPROFILE,
    [string]$OutDir = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..")) "artifacts\\storage-management"),
    [int]$TopCount = 25
)

$ErrorActionPreference = "Stop"

function Get-DirectoryBytes {
    param([string]$Path)
    try {
        $sum = Get-ChildItem -LiteralPath $Path -Force -Recurse -ErrorAction SilentlyContinue |
            Where-Object { -not $_.PSIsContainer } |
            Measure-Object -Property Length -Sum
        return [int64]($sum.Sum ?? 0)
    } catch {
        return [int64]0
    }
}

function Convert-ToGiB {
    param([double]$Bytes)
    if ($Bytes -le 0) { return 0.0 }
    return [math]::Round($Bytes / 1GB, 2)
}

function New-CloudCandidate {
    param([string]$Name, [string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        $item = Get-Item -LiteralPath $Path -Force
        $drive = Get-PSDrive -Name $item.PSDrive.Name -PSProvider FileSystem -ErrorAction Stop
        [pscustomobject]@{
            name = $Name
            path = $item.FullName
            drive = $drive.Name
            free_gb = Convert-ToGiB $drive.Free
            used_gb = Convert-ToGiB $drive.Used
            route_score = [math]::Round((($drive.Free / 1GB) * 1.0), 2)
        }
    } catch {
        $null
    }
}

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
$cloudCandidates = @(
    @{ name = "Dropbox"; path = (Join-Path $env:USERPROFILE "Dropbox") },
    @{ name = "GoogleDrive"; path = (Join-Path $env:USERPROFILE "Drive") },
    @{ name = "OneDrive"; path = (Join-Path $env:USERPROFILE "OneDrive") },
    @{ name = "ProtonDrive"; path = (Join-Path $env:USERPROFILE "Proton Drive") },
    @{ name = "AdobeCreativeCloud"; path = (Join-Path $env:USERPROFILE "Creative Cloud Files") },
    @{ name = "AdobeCreativeCloudAlt"; path = (Join-Path $env:USERPROFILE "Adobe Creative Cloud Files") }
)

$cloudRoots = foreach ($candidate in $cloudCandidates) {
    New-CloudCandidate -Name $candidate.name -Path $candidate.path
}

$cloudRoots = $cloudRoots | Where-Object { $_ } | Sort-Object route_score -Descending

$drives = Get-PSDrive -PSProvider FileSystem | ForEach-Object {
    [pscustomobject]@{
        name = $_.Name
        root = $_.Root
        free_gb = Convert-ToGiB $_.Free
        used_gb = Convert-ToGiB $_.Used
    }
}

$topLevel = foreach ($item in (Get-ChildItem -LiteralPath $resolvedRoot -Force -ErrorAction SilentlyContinue)) {
    if ($item.PSIsContainer) {
        $bytes = Get-DirectoryBytes -Path $item.FullName
        [pscustomobject]@{
            name = $item.Name
            path = $item.FullName
            kind = "directory"
            size_gb = Convert-ToGiB $bytes
        }
    } else {
        [pscustomobject]@{
            name = $item.Name
            path = $item.FullName
            kind = "file"
            size_gb = Convert-ToGiB $item.Length
        }
    }
}

$topLevel = $topLevel | Sort-Object size_gb -Descending

$largeFiles = Get-ChildItem -LiteralPath $resolvedRoot -Force -File -Recurse -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending |
    Select-Object -First $TopCount |
    ForEach-Object {
        [pscustomobject]@{
            path = $_.FullName
            size_gb = Convert-ToGiB $_.Length
            extension = $_.Extension
        }
    }

$cacheHints = @(
    (Join-Path $resolvedRoot "AppData\\Local\\Temp"),
    (Join-Path $resolvedRoot "AppData\\Local\\Packages"),
    (Join-Path $resolvedRoot "AppData\\Roaming\\protonmail\\bridge-v3\\gluon\\backend\\store"),
    (Join-Path $resolvedRoot ".cache"),
    (Join-Path $resolvedRoot ".npm"),
    (Join-Path $resolvedRoot ".nuget\\packages")
) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object {
    [pscustomobject]@{
        path = $_
        size_gb = Convert-ToGiB (Get-DirectoryBytes -Path $_)
    }
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    root = $resolvedRoot
    drives = $drives
    cloud_roots = $cloudRoots
    top_level = $topLevel | Select-Object -First $TopCount
    large_files = $largeFiles
    cache_hints = $cacheHints | Sort-Object size_gb -Descending
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$jsonPath = Join-Path $OutDir "scan-$stamp.json"
$mdPath = Join-Path $OutDir "scan-$stamp.md"

$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$lines = @()
$lines += "# Storage route scan"
$lines += ""
$lines += "- Generated: $($report.generated_at)"
$lines += "- Root: $($report.root)"
$lines += ""
$lines += "## Ranked cloud roots"
$lines += ""
foreach ($rootEntry in $cloudRoots) {
    $lines += "- $($rootEntry.name): $($rootEntry.path) | free $($rootEntry.free_gb) GB | score $($rootEntry.route_score)"
}
$lines += ""
$lines += "## Largest top-level entries"
$lines += ""
foreach ($entry in ($report.top_level | Select-Object -First 15)) {
    $lines += "- $($entry.size_gb) GB | $($entry.kind) | $($entry.path)"
}
$lines += ""
$lines += "## Cache/problem zones"
$lines += ""
foreach ($hint in ($report.cache_hints | Select-Object -First 15)) {
    $lines += "- $($hint.size_gb) GB | $($hint.path)"
}
$lines += ""
$lines += "## Largest files"
$lines += ""
foreach ($file in ($report.large_files | Select-Object -First 15)) {
    $lines += "- $($file.size_gb) GB | $($file.path)"
}

$lines -join "`r`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Output "JSON: $jsonPath"
Write-Output "MD:   $mdPath"
