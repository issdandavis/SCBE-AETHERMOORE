param(
    [switch]$Apply
)

$mode = if ($Apply) { "APPLY" } else { "DRY-RUN" }
Write-Host "`n===== SCBE Deep Cleanup ($mode) =====" -ForegroundColor Cyan
Write-Host ""

$totalFreed = 0

function Clean-Target {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path $Path)) {
        Write-Host "  [skip] $Label (not found)" -ForegroundColor DarkGray
        return
    }
    $size = (Get-ChildItem $Path -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    $sizeMB = [math]::Round($size / 1MB, 1)
    if ($sizeMB -lt 0.1) {
        Write-Host "  [skip] $Label (empty)" -ForegroundColor DarkGray
        return
    }
    $script:totalFreed += $sizeMB
    if ($Apply) {
        Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [DEL]  $sizeMB MB  $Label" -ForegroundColor Green
    } else {
        Write-Host "  [would delete]  $sizeMB MB  $Label" -ForegroundColor Yellow
    }
}

Write-Host "--- Temp Files ---"
# Clean old temp files (older than 1 day to avoid breaking active processes)
if (Test-Path 'C:\Users\issda\AppData\Local\Temp') {
    $tempItems = Get-ChildItem 'C:\Users\issda\AppData\Local\Temp' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) }
    $tempSize = ($tempItems | Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    $tempMB = [math]::Round($tempSize / 1MB, 1)
    $totalFreed += $tempMB
    if ($Apply) {
        $tempItems | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [DEL]  $tempMB MB  Temp files (>1 day old)" -ForegroundColor Green
    } else {
        Write-Host "  [would delete]  $tempMB MB  Temp files (>1 day old)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "--- Package Caches ---"
Clean-Target 'C:\Users\issda\AppData\Local\npm-cache' 'npm cache'
Clean-Target 'C:\Users\issda\AppData\Local\pip\cache' 'pip cache'
Clean-Target 'C:\Users\issda\.cache\pip' '.cache/pip'
Clean-Target 'C:\Users\issda\.cache\uv' '.cache/uv'
Clean-Target 'C:\Users\issda\.cache\huggingface\hub' '.cache/huggingface/hub (HF model cache)'

Write-Host ""
Write-Host "--- Build Artifacts ---"
Clean-Target 'C:\Users\issda\_oqs_build' 'liboqs build artifacts'
Clean-Target 'C:\Users\issda\SCBE-AETHERMOORE\.hypothesis' 'hypothesis test cache'
Clean-Target 'C:\Users\issda\SCBE-AETHERMOORE\dist' 'dist (npm build output)'
Clean-Target 'C:\Users\issda\SCBE-AETHERMOORE\.npm-cache' 'SCBE .npm-cache'

Write-Host ""
Write-Host "--- IDE / Tool Caches ---"
Clean-Target 'C:\Users\issda\.gemini' 'Gemini cache'
Clean-Target 'C:\Users\issda\.vs-kubernetes' 'VS Kubernetes tools cache'

Write-Host ""
Write-Host "--- Shopify App node_modules (reinstall with npm i) ---"
Clean-Target 'C:\Users\issda\lucrative-supply-app\node_modules' 'lucrative-supply-app/node_modules'
Clean-Target 'C:\Users\issda\growing-consumer-app\node_modules' 'growing-consumer-app/node_modules'
Clean-Target 'C:\Users\issda\empowered-account-app\node_modules' 'empowered-account-app/node_modules'
Clean-Target 'C:\Users\issda\node_modules' 'root node_modules'

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
$totalGB = [math]::Round($totalFreed / 1024, 2)
if ($Apply) {
    Write-Host "  Freed: $totalFreed MB ($totalGB GB)" -ForegroundColor Green
} else {
    Write-Host "  Would free: $totalFreed MB ($totalGB GB)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  To actually delete, run:" -ForegroundColor White
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/system/deep_cleanup.ps1 -Apply" -ForegroundColor White
}
Write-Host "====================================" -ForegroundColor Cyan

# Show new free space
$drive = Get-PSDrive C
$freeGB = [math]::Round($drive.Free / 1GB, 2)
Write-Host "  Current free space: $freeGB GB" -ForegroundColor Cyan
Write-Host ""
