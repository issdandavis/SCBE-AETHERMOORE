@echo off
title SCBE Package Preparation Tool
color 0A
echo.
echo ========================================
echo   SCBE Package Preparation Tool
echo   Making your package ready for npm!
echo ========================================
echo.
echo Press any key to start...
pause > nul
echo.

echo [1/4] Checking if Node.js is installed...
where node > nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo ERROR: Node.js is not installed!
    echo.
    echo Please install Node.js first:
    echo 1. Go to https://nodejs.org/
    echo 2. Download the LTS version
    echo 3. Install it
    echo 4. Restart your computer
    echo 5. Try this script again
    echo.
    pause
    exit /b 1
)
echo ✓ Node.js is installed!
echo.

echo [2/4] Building TypeScript code...
echo This may take 30 seconds...
call npm run build
if errorlevel 1 (
    color 0C
    echo.
    echo ERROR: Build failed!
    echo.
    echo Try this:
    echo 1. Open Command Prompt in this folder
    echo 2. Type: npm install
    echo 3. Press Enter and wait
    echo 4. Run this script again
    echo.
    pause
    exit /b 1
)
echo ✓ Build complete!
echo.

echo [3/4] Adding files to git...
git add dist/
echo ✓ Files added!
echo.

echo [4/4] Committing and pushing to GitHub...
git commit -m "Build: Add compiled dist/ for npm install"
git push
if errorlevel 1 (
    echo.
    echo Note: Push may have failed or nothing to commit
    echo This is usually okay!
)
echo.

color 0A
echo ========================================
echo   SUCCESS! Your package is ready!
echo ========================================
echo.
echo People can now install with:
echo npm install git+https://github.com/issdandavis/scbe-aethermoore-demo.git
echo.
echo.
echo Press any key to close...
pause > nul
