@echo off
REM ============================================================================
REM SCBE-AETHERMOORE v3.0.0 - Unified Build Script
REM ============================================================================
REM This script handles complete installation, build, and verification
REM for the SCBE-AETHERMOORE cryptographic framework.
REM
REM Author: Issac Daniel Davis
REM Date: January 18, 2026
REM License: MIT
REM ============================================================================

echo.
echo ============================================================================
echo SCBE-AETHERMOORE v3.0.0 - Unified Build System
echo ============================================================================
echo.

REM Check if running with admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] Not running as administrator. Some operations may fail.
    echo.
)

REM ============================================================================
REM STEP 1: ENVIRONMENT VERIFICATION
REM ============================================================================
echo [STEP 1/8] Verifying environment...
echo.

REM Check Node.js
where node >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18.0.0 or higher.
    echo Download: https://nodejs.org/
    exit /b 1
)

node --version
echo [OK] Node.js found

REM Check npm
where npm >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] npm not found. Please install npm.
    exit /b 1
)

npm --version
echo [OK] npm found

REM Check Python
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10 or higher.
    echo Download: https://www.python.org/downloads/
    exit /b 1
)

python --version
echo [OK] Python found

REM Check pip
where pip >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] pip not found. Please install pip.
    exit /b 1
)

pip --version
echo [OK] pip found

echo.
echo [STEP 1/8] Environment verification complete!
echo.

REM ============================================================================
REM STEP 2: CLEAN PREVIOUS BUILDS
REM ============================================================================
echo [STEP 2/8] Cleaning previous builds...
echo.

if exist dist rmdir /s /q dist
if exist node_modules rmdir /s /q node_modules
if exist __pycache__ rmdir /s /q __pycache__
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist htmlcov rmdir /s /q htmlcov
if exist .coverage del /q .coverage
if exist coverage.json del /q coverage.json
if exist *.tgz del /q *.tgz

echo [OK] Clean complete
echo.

REM ============================================================================
REM STEP 3: INSTALL NODE.JS DEPENDENCIES
REM ============================================================================
echo [STEP 3/8] Installing Node.js dependencies...
echo.

call npm install
if %errorLevel% neq 0 (
    echo [ERROR] npm install failed
    exit /b 1
)

echo [OK] Node.js dependencies installed
echo.

REM ============================================================================
REM STEP 4: INSTALL PYTHON DEPENDENCIES
REM ============================================================================
echo [STEP 4/8] Installing Python dependencies...
echo.

pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo [ERROR] pip install failed
    exit /b 1
)

echo [OK] Python dependencies installed
echo.

REM ============================================================================
REM STEP 5: BUILD TYPESCRIPT MODULES
REM ============================================================================
echo [STEP 5/8] Building TypeScript modules...
echo.

call npm run build
if %errorLevel% neq 0 (
    echo [ERROR] TypeScript build failed
    exit /b 1
)

echo [OK] TypeScript build complete
echo.

REM ============================================================================
REM STEP 6: RUN TESTS
REM ============================================================================
echo [STEP 6/8] Running test suite...
echo.

REM TypeScript tests
echo [6.1] Running TypeScript tests...
call npm test
if %errorLevel% neq 0 (
    echo [WARNING] TypeScript tests failed
    set TEST_FAILED=1
) else (
    echo [OK] TypeScript tests passed
)
echo.

REM Python tests
echo [6.2] Running Python tests...
python -m pytest tests/ -v --tb=short
if %errorLevel% neq 0 (
    echo [WARNING] Python tests failed
    set TEST_FAILED=1
) else (
    echo [OK] Python tests passed
)
echo.

if defined TEST_FAILED (
    echo [WARNING] Some tests failed. Review output above.
    echo.
)

REM ============================================================================
REM STEP 7: PACKAGE NPM MODULE
REM ============================================================================
echo [STEP 7/8] Packaging npm module...
echo.

call npm pack
if %errorLevel% neq 0 (
    echo [ERROR] npm pack failed
    exit /b 1
)

echo [OK] Package created: scbe-aethermoore-3.0.0.tgz
echo.

REM ============================================================================
REM STEP 8: VERIFICATION
REM ============================================================================
echo [STEP 8/8] Verifying build...
echo.

if not exist dist\src\index.js (
    echo [ERROR] Build verification failed: dist/src/index.js not found
    exit /b 1
)

if not exist scbe-aethermoore-3.0.0.tgz (
    echo [ERROR] Build verification failed: package tarball not found
    exit /b 1
)

echo [OK] Build verification complete
echo.

REM ============================================================================
REM BUILD SUMMARY
REM ============================================================================
echo ============================================================================
echo BUILD SUMMARY
echo ============================================================================
echo.
echo Status: SUCCESS
echo Package: scbe-aethermoore-3.0.0.tgz
echo Size: 
dir scbe-aethermoore-3.0.0.tgz | find "scbe-aethermoore"
echo.
echo TypeScript modules: dist/src/
echo Python modules: src/
echo.
echo Next steps:
echo   1. Test installation: npm install scbe-aethermoore-3.0.0.tgz
echo   2. Run demos: npm run demo
echo   3. Publish to npm: npm publish --access public
echo.
echo Documentation:
echo   - README.md (quick start)
echo   - QUICKSTART.md (5-minute tutorial)
echo   - HOW_TO_USE.md (detailed usage)
echo   - ARCHITECTURE_5_LAYERS.md (system architecture)
echo.
echo ============================================================================
echo.

if defined TEST_FAILED (
    echo [WARNING] Build completed with test failures. Review test output.
    exit /b 2
)

echo [SUCCESS] Build completed successfully!
exit /b 0
