param(
    [string]$OutDir = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")) "artifacts\pc-memory"),
    [int]$TopProcesses = 25,
    [int]$WarnRamPercent = 85,
    [int]$WarnDiskFreeGb = 25
)

$ErrorActionPreference = "Stop"

function Convert-ToGiB {
    param([double]$Bytes)
    if ($Bytes -le 0) { return 0.0 }
    return [math]::Round($Bytes / 1GB, 2)
}

function Convert-KiBToGiB {
    param([double]$KiB)
    if ($KiB -le 0) { return 0.0 }
    return [math]::Round($KiB / 1MB, 2)
}

function Get-DirectoryBytesShallow {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return [int64]0 }
    try {
        $sum = Get-ChildItem -LiteralPath $Path -Force -File -Recurse -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum
        if ($null -eq $sum.Sum) { return [int64]0 }
        return [int64]$sum.Sum
    } catch {
        return [int64]0
    }
}

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$os = Get-CimInstance Win32_OperatingSystem
$totalRamGb = Convert-KiBToGiB $os.TotalVisibleMemorySize
$freeRamGb = Convert-KiBToGiB $os.FreePhysicalMemory
$usedRamGb = [math]::Round($totalRamGb - $freeRamGb, 2)
$usedRamPct = if ($totalRamGb -gt 0) { [math]::Round(($usedRamGb / $totalRamGb) * 100, 1) } else { 0 }

$pageFiles = Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{
        name = $_.Name
        allocated_mb = $_.AllocatedBaseSize
        current_mb = $_.CurrentUsage
        peak_mb = $_.PeakUsage
    }
}

$drives = Get-PSDrive -PSProvider FileSystem | ForEach-Object {
    [pscustomobject]@{
        name = $_.Name
        root = $_.Root
        free_gb = Convert-ToGiB $_.Free
        used_gb = Convert-ToGiB $_.Used
        low_free_space = ((Convert-ToGiB $_.Free) -lt $WarnDiskFreeGb)
    }
}

$processes = Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First $TopProcesses | ForEach-Object {
    [pscustomobject]@{
        name = $_.ProcessName
        id = $_.Id
        ram_mb = [math]::Round($_.WorkingSet64 / 1MB, 1)
        private_mb = [math]::Round($_.PrivateMemorySize64 / 1MB, 1)
        path = $_.Path
    }
}

$cloudRoots = @(
    (Join-Path $env:USERPROFILE "OneDrive"),
    (Join-Path $env:USERPROFILE "Dropbox"),
    (Join-Path $env:USERPROFILE "Drive"),
    (Join-Path $env:USERPROFILE "Google Drive"),
    (Join-Path $env:USERPROFILE "Proton Drive")
) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object {
    $item = Get-Item -LiteralPath $_ -Force
    [pscustomobject]@{
        path = $item.FullName
        attributes = [string]$item.Attributes
        last_write_time = $item.LastWriteTime.ToString("o")
    }
}

$cachePaths = @(
    (Join-Path $env:USERPROFILE "AppData\Local\Temp"),
    (Join-Path $env:USERPROFILE ".cache"),
    (Join-Path $env:USERPROFILE ".npm"),
    (Join-Path $env:USERPROFILE ".nuget\packages"),
    (Join-Path $env:USERPROFILE "AppData\Local\pip\Cache"),
    (Join-Path $env:USERPROFILE "AppData\Local\Microsoft\Windows\INetCache")
) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object {
    [pscustomobject]@{
        path = $_
        size_gb = Convert-ToGiB (Get-DirectoryBytesShallow $_)
    }
}

$warnings = New-Object System.Collections.Generic.List[string]
if ($usedRamPct -ge $WarnRamPercent) {
    [void]$warnings.Add("High RAM pressure: $usedRamPct% used. Close or restart top memory processes before long builds.")
}
foreach ($drive in $drives) {
    if ($drive.low_free_space) {
        [void]$warnings.Add("Low disk headroom on $($drive.root): $($drive.free_gb) GB free.")
    }
}
$oneDriveProc = $processes | Where-Object { $_.name -like "OneDrive*" } | Select-Object -First 1
if ($oneDriveProc -and $oneDriveProc.ram_mb -gt 1000) {
    [void]$warnings.Add("OneDrive is using $($oneDriveProc.ram_mb) MB RAM. Pause sync during builds or recovery scans.")
}

$recommendations = @(
    "Keep at least 20-25 GB free on C: before builds, PQC compiles, browser automation, or repo-wide scans.",
    "Pause OneDrive while running large recursive scans, installs, or backups.",
    "Prefer shallow health scans first; run deep storage scans only when RAM is below 80% used.",
    "Treat cloud roots as backup targets only with self-nesting excludes.",
    "Do not delete caches automatically; review cache hotspots and clear them with app-aware tools."
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    machine = $env:COMPUTERNAME
    user = $env:USERNAME
    ram = [ordered]@{
        total_gb = $totalRamGb
        used_gb = $usedRamGb
        free_gb = $freeRamGb
        used_percent = $usedRamPct
    }
    pagefiles = $pageFiles
    drives = $drives
    top_processes = $processes
    cloud_roots = $cloudRoots
    cache_hotspots = $cachePaths | Sort-Object size_gb -Descending
    warnings = $warnings
    recommendations = $recommendations
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$jsonPath = Join-Path $OutDir "pc-memory-health-$stamp.json"
$mdPath = Join-Path $OutDir "pc-memory-health-$stamp.md"

$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$lines = @()
$lines += "# PC Memory Health"
$lines += ""
$lines += "- Generated: $($report.generated_at)"
$lines += "- Machine: $($report.machine)"
$lines += "- User: $($report.user)"
$lines += ""
$lines += "## RAM"
$lines += ""
$lines += "- Total: $($report.ram.total_gb) GB"
$lines += "- Used: $($report.ram.used_gb) GB ($($report.ram.used_percent)%)"
$lines += "- Free: $($report.ram.free_gb) GB"
$lines += ""
$lines += "## Warnings"
$lines += ""
if ($warnings.Count -eq 0) {
    $lines += "- None"
} else {
    foreach ($warning in $warnings) { $lines += "- $warning" }
}
$lines += ""
$lines += "## Top Processes"
$lines += ""
foreach ($proc in ($processes | Select-Object -First 15)) {
    $lines += "- $($proc.ram_mb) MB | $($proc.name) | pid $($proc.id)"
}
$lines += ""
$lines += "## Drives"
$lines += ""
foreach ($drive in $drives) {
    $lines += "- $($drive.root) free $($drive.free_gb) GB, used $($drive.used_gb) GB"
}
$lines += ""
$lines += "## Cache Hotspots"
$lines += ""
foreach ($cache in ($report.cache_hotspots | Select-Object -First 10)) {
    $lines += "- $($cache.size_gb) GB | $($cache.path)"
}
$lines += ""
$lines += "## Recommendations"
$lines += ""
foreach ($rec in $recommendations) { $lines += "- $rec" }

$lines -join "`r`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Output "JSON: $jsonPath"
Write-Output "MD:   $mdPath"
if ($warnings.Count -gt 0) {
    Write-Output "WARNINGS:"
    foreach ($warning in $warnings) { Write-Output "- $warning" }
}
