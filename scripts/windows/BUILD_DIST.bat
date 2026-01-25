@echo off
REM SCBE-AETHERMOORE Distribution Builder
REM Creates a clean, standalone package in Downloads folder

set DIST_NAME=SCBE-AETHERMOORE-v3.0.0
set DIST_PATH=%USERPROFILE%\Downloads\%DIST_NAME%

echo Creating distribution package: %DIST_PATH%

REM Clean and create distribution folder
if exist "%DIST_PATH%" rmdir /s /q "%DIST_PATH%"
mkdir "%DIST_PATH%"

REM Copy source code
xcopy /E /I /Y "src" "%DIST_PATH%\src"
xcopy /E /I /Y "tests" "%DIST_PATH%\tests"
xcopy /E /I /Y "demo" "%DIST_PATH%\demo"
xcopy /E /I /Y "examples" "%DIST_PATH%\examples"
xcopy /E /I /Y "docs" "%DIST_PATH%\docs"
xcopy /E /I /Y "config" "%DIST_PATH%\config"

REM Copy essential files
copy /Y "package.json" "%DIST_PATH%\"
copy /Y "package-lock.json" "%DIST_PATH%\"
copy /Y "tsconfig.json" "%DIST_PATH%\"
copy /Y "tsconfig.base.json" "%DIST_PATH%\"
copy /Y "vitest.config.ts" "%DIST_PATH%\"
copy /Y "LICENSE" "%DIST_PATH%\"
copy /Y "README.md" "%DIST_PATH%\"
copy /Y "QUICKSTART.md" "%DIST_PATH%\"
copy /Y "CHANGELOG.md" "%DIST_PATH%\"
copy /Y "CONTRIBUTING.md" "%DIST_PATH%\"
copy /Y "DEPLOYMENT.md" "%DIST_PATH%\"
copy /Y "FEATURES.md" "%DIST_PATH%\"
copy /Y ".env.example" "%DIST_PATH%\"
copy /Y ".prettierrc" "%DIST_PATH%\"
copy /Y ".prettierignore" "%DIST_PATH%\"
copy /Y ".npmignore" "%DIST_PATH%\"
copy /Y "Dockerfile" "%DIST_PATH%\"
copy /Y "docker-compose.yml" "%DIST_PATH%\"

REM Copy Python files
copy /Y "scbe-cli.py" "%DIST_PATH%\"
copy /Y "scbe_demo.py" "%DIST_PATH%\"
copy /Y "harmonic_scaling_law.py" "%DIST_PATH%\"
copy /Y "spiralverse_sdk.py" "%DIST_PATH%\"
copy /Y "requirements.txt" "%DIST_PATH%\"

REM Copy specification
copy /Y "docs\SPECIFICATION.md" "%DIST_PATH%\SPECIFICATION.md"

echo.
echo Distribution created at: %DIST_PATH%
echo.
echo To use the package:
echo   1. cd %DIST_PATH%
echo   2. npm install
echo   3. npm run build
echo   4. npm test
echo.
echo Or open demo\index.html in a browser for the interactive demo.
pause
