param(
    [string]$RepoPath = "C:/Users/issda/SCBE-AETHERMOORE",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path $RepoPath

$targets = @(
    "$repo/.pytest_cache",
    "$repo/.hypothesis/examples",
    "$repo/artifacts/pytest_tmp",
    "$repo/__pycache__",
    "$repo/src/__pycache__",
    "$repo/tests/__pycache__"
)

Write-Host "Cleanup mode: $([string]::Join('', @($(if($Apply){'APPLY'}else{'DRY-RUN'}))))"

foreach ($t in $targets) {
    if (Test-Path $t) {
        $size = (Get-ChildItem -LiteralPath $t -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        $gb = [Math]::Round(($size / 1GB), 4)
        if ($Apply) {
            Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "Removed: $t ($gb GB)"
        } else {
            Write-Host "Would remove: $t ($gb GB)"
        }
    }
}

if (-not $Apply) {
    Write-Host "No files deleted. Re-run with -Apply to perform cleanup."
}
