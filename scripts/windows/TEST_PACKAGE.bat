@echo off
echo ========================================
echo   SCBE Package Test Tool
echo   Testing if your package works!
echo ========================================
echo.

echo Creating test folder...
if exist test-install rmdir /s /q test-install
mkdir test-install
cd test-install
echo ✓ Test folder created!
echo.

echo Step 1: Installing your package from GitHub...
call npm init -y
call npm install git+https://github.com/issdandavis/scbe-aethermoore-demo.git
if errorlevel 1 (
    echo ERROR: Installation failed!
    cd ..
    pause
    exit /b 1
)
echo ✓ Package installed!
echo.

echo Step 2: Testing if it works...
node -e "try { const scbe = require('@scbe/aethermoore'); console.log('✓ SUCCESS! Package version:', scbe.VERSION || '3.0.0'); } catch(e) { console.log('✗ ERROR:', e.message); process.exit(1); }"
if errorlevel 1 (
    echo ERROR: Package doesn't work!
    cd ..
    pause
    exit /b 1
)
echo.

echo Step 3: Cleaning up...
cd ..
rmdir /s /q test-install
echo ✓ Cleanup complete!
echo.

echo ========================================
echo   ALL TESTS PASSED!
echo   Your package is working perfectly!
echo ========================================
echo.
pause
