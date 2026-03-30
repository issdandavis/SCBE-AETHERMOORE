param(
    [string]$ScanJson = "",
    [string]$OutDir = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..")) "artifacts\\storage-management")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

if ([string]::IsNullOrWhiteSpace($ScanJson)) {
    $ScanJson = Get-ChildItem -LiteralPath $OutDir -Filter "scan-*.json" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}

if (-not $ScanJson) {
    throw "No scan JSON found. Run storage_route_scan.ps1 first."
}

$scan = Get-Content -LiteralPath $ScanJson -Raw | ConvertFrom-Json

$cloudRootPaths = @($scan.cloud_roots | ForEach-Object { $_.path })
$bestRoute = $scan.cloud_roots | Sort-Object route_score -Descending | Select-Object -First 1
$actions = New-Object System.Collections.Generic.List[object]

foreach ($entry in $scan.top_level) {
    $path = [string]$entry.path
    $name = [string]$entry.name
    $size = [double]$entry.size_gb

    if ($cloudRootPaths -contains $path) {
        $actions.Add([pscustomobject]@{
            scope = $path
            category = "cloud-root"
            action = "exclude-from-profile-backup"
            reason = "Avoid recursive sync and duplicate copies."
        })
        continue
    }

    if ($path -like "*\\AppData*" -or $name -in @("AppData", ".cache", ".npm", ".nuget")) {
        $actions.Add([pscustomobject]@{
            scope = $path
            category = "cache-or-runtime"
            action = "review-for-cleanup-or-exclude"
            reason = "Runtime caches bloat backups and usually do not need cloud mirror treatment."
        })
        continue
    }

    if ($name -eq "Downloads") {
        $actions.Add([pscustomobject]@{
            scope = $path
            category = "user-ingest"
            action = "archive-old-installers-and-zips"
            reason = "Downloads usually contains one-time payloads and duplicate installers."
        })
        continue
    }

    if ($name -in @("Desktop", "Documents", "Pictures", "Videos", "Music")) {
        $actions.Add([pscustomobject]@{
            scope = $path
            category = "user-content"
            action = "keep-and-back-up"
            reason = "Primary user content should stay in the protected set."
        })
        continue
    }

    if ($size -ge 5) {
        $actions.Add([pscustomobject]@{
            scope = $path
            category = "large-root"
            action = "inspect-before-move"
            reason = "Large top-level folder needs classification before any move."
        })
    }
}

$cacheActions = foreach ($hint in $scan.cache_hints) {
    [pscustomobject]@{
        scope = [string]$hint.path
        category = "cache-hotspot"
        action = "exclude-from-cloud-backup"
        reason = "Known cache or mail-store hotspot. Handle separately."
    }
}

foreach ($item in $cacheActions) { $actions.Add($item) }

$plan = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    source_scan = $ScanJson
    recommended_target = $bestRoute
    actions = $actions
    robocopy_excludes = @(
        $cloudRootPaths +
        ($scan.cache_hints | ForEach-Object { $_.path })
    ) | Where-Object { $_ } | Select-Object -Unique
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$jsonPath = Join-Path $OutDir "sort-plan-$stamp.json"
$mdPath = Join-Path $OutDir "sort-plan-$stamp.md"

$plan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$lines = @()
$lines += "# Storage sort plan"
$lines += ""
$lines += "- Generated: $($plan.generated_at)"
$lines += "- Source scan: $($plan.source_scan)"
$lines += ""
if ($bestRoute) {
    $lines += "## Recommended target"
    $lines += ""
    $lines += "- $($bestRoute.name): $($bestRoute.path) | free $($bestRoute.free_gb) GB"
    $lines += ""
}
$lines += "## Actions"
$lines += ""
foreach ($action in $actions) {
    $lines += "- [$($action.category)] $($action.action) | $($action.scope)"
    $lines += "  Reason: $($action.reason)"
}
$lines += ""
$lines += "## Exclude list for profile backup"
$lines += ""
foreach ($path in $plan.robocopy_excludes) {
    $lines += "- $path"
}

$lines -join "`r`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Output "JSON: $jsonPath"
Write-Output "MD:   $mdPath"
