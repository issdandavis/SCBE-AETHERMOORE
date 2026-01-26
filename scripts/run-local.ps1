# ===========================================
# SCBE-AETHERMOORE Local Development Runner
# ===========================================
# PowerShell script for Windows
#
# Usage: .\scripts\run-local.ps1
#
# Requirements:
#   - Python 3.10+
#   - Git (to clone if needed)

$ErrorActionPreference = "Continue"

Write-Host "=========================================" -ForegroundColor Blue
Write-Host "  SCBE-AETHERMOORE Local Runner" -ForegroundColor Blue
Write-Host "=========================================" -ForegroundColor Blue

# Find project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

Write-Host "`nProject root: $ProjectRoot" -ForegroundColor Yellow

# Check Python
Write-Host "`nChecking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
python -m pip install --quiet --upgrade pip 2>$null
python -m pip install --quiet fastapi uvicorn pydantic numpy scipy 2>$null

if (Test-Path "requirements.txt") {
    python -m pip install --quiet -r requirements.txt 2>$null
}

# Create .env if needed
if (-not (Test-Path ".env")) {
    Write-Host "`nCreating .env file..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
    } else {
        @"
SCBE_API_KEY=dev-key-local
SCBE_MODE=development
LOG_LEVEL=INFO
"@ | Out-File -FilePath ".env" -Encoding UTF8
    }
}

# Start API
Write-Host "`n=========================================" -ForegroundColor Blue
Write-Host "  Starting SCBE Core API" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "  API:      http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Docs:     http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Health:   http://localhost:8000/v1/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

Set-Location "$ProjectRoot\api"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
