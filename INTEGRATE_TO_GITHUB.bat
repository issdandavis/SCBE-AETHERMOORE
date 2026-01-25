@echo off
REM Integration Script: Copy SCBE Production Pack to SCBE-AETHERMOORE GitHub Repo
REM
REM Usage:
REM   1. Update GITHUB_REPO_PATH below if needed
REM   2. Run: INTEGRATE_TO_GITHUB.bat
REM   3. Review changes
REM   4. Commit and push to GitHub

setlocal enabledelayedexpansion

REM Configuration
set GITHUB_REPO_PATH=C:\Users\issda\Downloads\SCBE-AETHERMOORE
set CURRENT_DIR=%CD%

echo ==================================================
echo SCBE Production Pack -^> GitHub Integration
echo ==================================================
echo.
echo Source: %CURRENT_DIR%
echo Target: %GITHUB_REPO_PATH%
echo.

REM Check if GitHub repo exists
if not exist "%GITHUB_REPO_PATH%" (
    echo ERROR: GitHub repo not found at %GITHUB_REPO_PATH%
    echo.
    echo Please clone it first:
    echo   cd C:\Users\issda\Downloads
    echo   git clone https://github.com/issdandavis/SCBE-AETHERMOORE.git
    exit /b 1
)

echo Step 1: Creating directory structure...
mkdir "%GITHUB_REPO_PATH%\symphonic_cipher\core" 2>nul
mkdir "%GITHUB_REPO_PATH%\symphonic_cipher\geoseal" 2>nul
mkdir "%GITHUB_REPO_PATH%\symphonic_cipher\spiralverse\tongues" 2>nul
mkdir "%GITHUB_REPO_PATH%\symphonic_cipher\pqc" 2>nul
mkdir "%GITHUB_REPO_PATH%\symphonic_cipher\topology" 2>nul
mkdir "%GITHUB_REPO_PATH%\symphonic_cipher\dynamics" 2>nul
mkdir "%GITHUB_REPO_PATH%\symphonic_cipher\connectors" 2>nul
mkdir "%GITHUB_REPO_PATH%\symphonic_cipher\audio" 2>nul
mkdir "%GITHUB_REPO_PATH%\scbe" 2>nul
mkdir "%GITHUB_REPO_PATH%\tests" 2>nul
mkdir "%GITHUB_REPO_PATH%\examples" 2>nul
mkdir "%GITHUB_REPO_PATH%\docs" 2>nul
mkdir "%GITHUB_REPO_PATH%\config" 2>nul
echo √ Directory structure created
echo.

echo Step 2: Copying core SCBE implementation...
copy "src\scbe_14layer_reference.py" "%GITHUB_REPO_PATH%\scbe\pipeline.py" >nul
echo √ scbe\pipeline.py
echo.

echo Step 3: Copying GeoSeal manifold...
copy "symphonic_cipher_geoseal_manifold.py" "%GITHUB_REPO_PATH%\symphonic_cipher\geoseal\manifold.py" >nul
echo √ symphonic_cipher\geoseal\manifold.py
echo.

echo Step 4: Copying Spiralverse SDK...
copy "symphonic_cipher_spiralverse_sdk.py" "%GITHUB_REPO_PATH%\symphonic_cipher\spiralverse\sdk.py" >nul
echo √ symphonic_cipher\spiralverse\sdk.py
echo.

echo Step 5: Copying tests...
copy "tests\test_scbe_14layers.py" "%GITHUB_REPO_PATH%\tests\" >nul
echo √ tests\test_scbe_14layers.py
echo.

echo Step 6: Copying examples...
copy "examples\demo_integrated_system.py" "%GITHUB_REPO_PATH%\examples\" >nul
copy "examples\demo_scbe_system.py" "%GITHUB_REPO_PATH%\examples\" >nul
echo √ examples\demo_integrated_system.py
echo √ examples\demo_scbe_system.py
echo.

echo Step 7: Copying documentation...
copy "docs\WHAT_YOU_BUILT.md" "%GITHUB_REPO_PATH%\docs\" >nul
copy "docs\GEOSEAL_CONCEPT.md" "%GITHUB_REPO_PATH%\docs\" >nul
copy "docs\DEMONSTRATION_SUMMARY.md" "%GITHUB_REPO_PATH%\docs\" >nul
copy "docs\AWS_LAMBDA_DEPLOYMENT.md" "%GITHUB_REPO_PATH%\docs\" >nul
copy "docs\COMPREHENSIVE_MATH_SCBE.md" "%GITHUB_REPO_PATH%\docs\" >nul
copy "docs\LANGUES_WEIGHTING_SYSTEM.md" "%GITHUB_REPO_PATH%\docs\" >nul
copy "docs\GITHUB_INTEGRATION_GUIDE.md" "%GITHUB_REPO_PATH%\docs\" >nul
echo √ Documentation files copied
echo.

echo Step 8: Copying configuration...
if exist "config\scbe.alerts.yml" (
    copy "config\scbe.alerts.yml" "%GITHUB_REPO_PATH%\config\" >nul
    copy "config\sentinel.yml" "%GITHUB_REPO_PATH%\config\" >nul
    copy "config\steward.yml" "%GITHUB_REPO_PATH%\config\" >nul
    echo √ Configuration files copied
) else (
    echo ! Configuration files not found ^(optional^)
)
echo.

echo Step 9: Copying README...
copy "README.md" "%GITHUB_REPO_PATH%\" >nul
echo √ README.md
echo.

echo Step 10: Creating __init__.py files...

REM Root package
(
echo """
echo SCBE-AETHERMOORE v3.0 - Symphonic Cipher Library
echo Patent Pending: USPTO #63/961,403
echo.
echo Quantum-Resistant Hyperbolic Geometry AI Safety Framework
echo """
echo.
echo __version__ = "3.0.0"
echo __author__ = "Issac Davis"
echo __patent__ = "USPTO #63/961,403"
echo.
echo # Core components
echo from .geoseal.manifold import GeoSealManifold
echo from .spiralverse.sdk import SpiralverseSDK, SacredTongue
echo.
echo __all__ = [
echo     'GeoSealManifold',
echo     'SpiralverseSDK',
echo     'SacredTongue',
echo ]
) > "%GITHUB_REPO_PATH%\symphonic_cipher\__init__.py"

REM GeoSeal package
(
echo """GeoSeal Geometric Trust Manifold"""
echo from .manifold import GeoSealManifold
echo.
echo __all__ = ['GeoSealManifold']
) > "%GITHUB_REPO_PATH%\symphonic_cipher\geoseal\__init__.py"

REM Spiralverse package
(
echo """Spiralverse Protocol with Six Sacred Tongues"""
echo from .sdk import SpiralverseSDK, SacredTongue
echo.
echo __all__ = ['SpiralverseSDK', 'SacredTongue']
) > "%GITHUB_REPO_PATH%\symphonic_cipher\spiralverse\__init__.py"

REM Empty __init__.py for other packages
type nul > "%GITHUB_REPO_PATH%\symphonic_cipher\core\__init__.py"
type nul > "%GITHUB_REPO_PATH%\symphonic_cipher\pqc\__init__.py"
type nul > "%GITHUB_REPO_PATH%\symphonic_cipher\topology\__init__.py"
type nul > "%GITHUB_REPO_PATH%\symphonic_cipher\dynamics\__init__.py"
type nul > "%GITHUB_REPO_PATH%\symphonic_cipher\connectors\__init__.py"
type nul > "%GITHUB_REPO_PATH%\symphonic_cipher\audio\__init__.py"
type nul > "%GITHUB_REPO_PATH%\symphonic_cipher\spiralverse\tongues\__init__.py"
type nul > "%GITHUB_REPO_PATH%\scbe\__init__.py"

echo √ __init__.py files created
echo.

echo Step 11: Creating KIRO system map...
copy "KIRO_SYSTEM_MAP.md" "%GITHUB_REPO_PATH%\" >nul
echo √ KIRO_SYSTEM_MAP.md
echo.

echo ==================================================
echo Integration Complete!
echo ==================================================
echo.
echo Files copied to: %GITHUB_REPO_PATH%
echo.
echo Next steps:
echo   1. Review the changes:
echo      cd %GITHUB_REPO_PATH%
echo      git status
echo.
echo   2. Test the integration:
echo      python examples\demo_integrated_system.py
echo.
echo   3. Commit and push:
echo      git add .
echo      git commit -m "Complete integration: SCBE + GeoSeal + Spiralverse"
echo      git push origin main
echo.
echo   4. View on GitHub:
echo      https://github.com/issdandavis/SCBE-AETHERMOORE
echo.
pause
