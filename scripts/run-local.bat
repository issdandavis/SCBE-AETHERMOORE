@echo off
REM ===========================================
REM SCBE-AETHERMOORE Local Development Runner
REM ===========================================
REM Runs the full system without Docker
REM
REM Usage: scripts\run-local.bat
REM
REM Requirements:
REM   - Python 3.10+
REM   - Node.js 18+ (optional)

setlocal EnableDelayedExpansion

echo =========================================
echo   SCBE-AETHERMOORE Local Runner
echo =========================================

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

cd /d "%PROJECT_ROOT%"

REM Check Python
echo.
echo Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Install dependencies
echo.
echo Installing Python dependencies...
python -m pip install -q -r requirements.txt 2>nul
python -m pip install -q fastapi uvicorn pydantic 2>nul

REM Create .env if not exists
if not exist .env (
    echo.
    echo Creating .env file...
    if exist .env.example (
        copy .env.example .env >nul
    ) else (
        echo SCBE_API_KEY=dev-key-local> .env
        echo SCBE_MODE=development>> .env
        echo LOG_LEVEL=INFO>> .env
    )
)

REM Start API
echo.
echo =========================================
echo   Starting SCBE Core API
echo =========================================
echo.
echo   API:      http://localhost:8000
echo   Docs:     http://localhost:8000/docs
echo   Health:   http://localhost:8000/v1/health
echo.
echo   Press Ctrl+C to stop
echo.

cd "%PROJECT_ROOT%\api"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
