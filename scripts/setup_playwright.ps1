<#
.SYNOPSIS
    Lightweight Playwright setup for SCBE-AETHERMOORE headless browser automation.

.DESCRIPTION
    Installs Playwright via pip and downloads ONLY Chromium to conserve disk space.
    Skips Firefox (~200MB) and WebKit (~300MB) to save ~500MB total.
    Designed for systems with limited free space (2GB+).

.NOTES
    System: Windows 11, Python 3.14
    Disk budget: ~350MB (Chromium only)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup_playwright.ps1
#>

param(
    [switch]$SkipPipInstall,
    [switch]$Force,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SCBE-AETHERMOORE Playwright Setup" -ForegroundColor Cyan
Write-Host "  Chromium-only (disk-saving mode)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------
# 1. Check disk space
# ------------------------------------------------------------------
$drive = (Get-Item $PSScriptRoot).PSDrive
$freeGB = [math]::Round((Get-PSDrive $drive.Name).Free / 1GB, 2)
Write-Host "[1/5] Disk space on $($drive.Name):\  $freeGB GB free" -ForegroundColor Yellow

if ($freeGB -lt 1.0) {
    Write-Host "  WARNING: Less than 1 GB free. Playwright Chromium needs ~350 MB." -ForegroundColor Red
    if (-not $Force) {
        Write-Host "  Use -Force to proceed anyway." -ForegroundColor Red
        exit 1
    }
}

# ------------------------------------------------------------------
# 2. Check Python
# ------------------------------------------------------------------
Write-Host "[2/5] Checking Python..." -ForegroundColor Yellow
try {
    $pyVer = & python --version 2>&1
    Write-Host "  Found: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found in PATH." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------
# 3. Install playwright pip package
# ------------------------------------------------------------------
if (-not $SkipPipInstall) {
    Write-Host "[3/5] Installing playwright via pip..." -ForegroundColor Yellow
    & python -m pip install --upgrade playwright 2>&1 | ForEach-Object {
        if ($Verbose) { Write-Host "  $_" }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: pip install playwright failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "  playwright pip package installed." -ForegroundColor Green
} else {
    Write-Host "[3/5] Skipping pip install (--SkipPipInstall)." -ForegroundColor DarkGray
}

# ------------------------------------------------------------------
# 4. Install ONLY Chromium browser (saves ~500MB vs full install)
# ------------------------------------------------------------------
Write-Host "[4/5] Installing Chromium browser only..." -ForegroundColor Yellow
Write-Host "  (Skipping Firefox and WebKit to save disk space)" -ForegroundColor DarkGray

& python -m playwright install chromium 2>&1 | ForEach-Object {
    Write-Host "  $_"
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: playwright install chromium failed." -ForegroundColor Red
    Write-Host "  Try: python -m playwright install --with-deps chromium" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Chromium installed successfully." -ForegroundColor Green

# ------------------------------------------------------------------
# 5. Verify installation
# ------------------------------------------------------------------
Write-Host "[5/5] Verifying installation..." -ForegroundColor Yellow

$verifyScript = @"
import sys
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('data:text/html,<h1>SCBE Playwright OK</h1>')
        title = page.title()
        browser.close()
    print(f'  Chromium headless: PASS')
    sys.exit(0)
except Exception as e:
    print(f'  Chromium headless: FAIL - {e}')
    sys.exit(1)
"@

& python -c $verifyScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Verification failed. Chromium may need system deps." -ForegroundColor Red
    Write-Host "  Try: python -m playwright install --with-deps chromium" -ForegroundColor Yellow
    exit 1
}

# ------------------------------------------------------------------
# Done
# ------------------------------------------------------------------
$freeGBAfter = [math]::Round((Get-PSDrive $drive.Name).Free / 1GB, 2)
$usedMB = [math]::Round(($freeGB - $freeGBAfter) * 1024, 0)

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "  Disk used: ~${usedMB} MB" -ForegroundColor Green
Write-Host "  Remaining: $freeGBAfter GB free" -ForegroundColor Green
Write-Host "" -ForegroundColor Green
Write-Host "  Quick test:" -ForegroundColor Green
Write-Host "    python scripts\headless_browser.py --url https://example.com --action screenshot" -ForegroundColor White
Write-Host "    python scripts\headless_browser.py --url https://example.com --action extract" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
