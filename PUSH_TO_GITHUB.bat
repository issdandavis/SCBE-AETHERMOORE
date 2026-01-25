@echo off
title Push to GitHub
color 0A
echo.
echo ========================================
echo   Push Package to GitHub
echo ========================================
echo.
echo This will upload the dist/ folder to GitHub
echo so people can install your package with npm
echo.
echo Press any key to continue...
pause > nul
echo.

echo [1/3] Adding dist/ folder to git...
git add dist/
echo ✓ Done!
echo.

echo [2/3] Creating commit...
git commit -m "Build: Add compiled dist/ for npm install from GitHub"
if errorlevel 1 (
    echo.
    echo Note: Nothing new to commit (that's okay!)
    echo.
)
echo.

echo [3/3] Pushing to GitHub...
git push
if errorlevel 1 (
    color 0C
    echo.
    echo ERROR: Push failed!
    echo.
    echo This might mean:
    echo - You need to login to GitHub
    echo - No internet connection
    echo.
    echo Try opening GitHub Desktop and pushing from there
    echo.
    pause
    exit /b 1
)

color 0A
echo.
echo ========================================
echo   SUCCESS! Package is on GitHub!
echo ========================================
echo.
echo Anyone can now install with:
echo npm install git+https://github.com/issdandavis/scbe-aethermoore-demo.git
echo.
echo.
echo Press any key to close...
pause > nul
