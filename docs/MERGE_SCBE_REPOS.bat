@echo off
echo ============================================
echo SCBE Repository Merger
echo ============================================
echo.

cd /d C:\Users\issda\Downloads

echo Step 1: Cloning aws-lambda-simple-web-app (most complete repo)...
if exist SCBE_MERGED rmdir /s /q SCBE_MERGED
git clone https://github.com/issdandavis/aws-lambda-simple-web-app.git SCBE_MERGED
if errorlevel 1 (
    echo ERROR: Failed to clone. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo Step 2: Copying newer SpiralSeal with Sacred Tongues...
xcopy /E /Y /I "SCBE_Production_Pack\src\symphonic_cipher\scbe_aethermoore\spiral_seal" "SCBE_MERGED\symphonic_cipher\scbe_aethermoore\spiral_seal\"

echo.
echo Step 3: Copying docs...
xcopy /E /Y /I "SCBE_Production_Pack\docs" "SCBE_MERGED\docs\"

echo.
echo Step 4: Copying config...
xcopy /E /Y /I "SCBE_Production_Pack\config" "SCBE_MERGED\config\"

echo.
echo Step 5: Copying examples...
xcopy /E /Y /I "SCBE_Production_Pack\examples" "SCBE_MERGED\examples\"

echo.
echo Step 6: Copying TypeScript crypto envelope...
if not exist "SCBE_MERGED\src" mkdir "SCBE_MERGED\src"
xcopy /E /Y /I "SCBE_Production_Pack\src\crypto" "SCBE_MERGED\src\crypto\"
xcopy /E /Y /I "SCBE_Production_Pack\src\metrics" "SCBE_MERGED\src\metrics\"
xcopy /E /Y /I "SCBE_Production_Pack\src\rollout" "SCBE_MERGED\src\rollout\"
xcopy /E /Y /I "SCBE_Production_Pack\src\selfHealing" "SCBE_MERGED\src\selfHealing\"

echo.
echo Step 7: Copying tests...
xcopy /E /Y /I "SCBE_Production_Pack\tests" "SCBE_MERGED\tests\"

echo.
echo Step 8: Copying Python core files...
copy /Y "SCBE_Production_Pack\src\scbe_cpse_unified.py" "SCBE_MERGED\src\"
copy /Y "SCBE_Production_Pack\src\scbe_14layer_reference.py" "SCBE_MERGED\src\"
copy /Y "SCBE_Production_Pack\src\aethermoore.py" "SCBE_MERGED\src\"

echo.
echo Step 9: Pushing to SCBE-AETHERMOORE as canonical repo...
cd SCBE_MERGED
git remote set-url origin https://github.com/issdandavis/SCBE-AETHERMOORE.git
git add .
git commit -m "feat: Merge all SCBE repos - complete symphonic_cipher with Sacred Tongues SS1"
git push -f origin main

echo.
echo ============================================
echo DONE! All repos merged into SCBE-AETHERMOORE
echo ============================================
echo.
echo Your canonical repo is now at:
echo https://github.com/issdandavis/SCBE-AETHERMOORE
echo.
pause
