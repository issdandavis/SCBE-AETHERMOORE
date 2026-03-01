@echo off
setlocal

set "SCBE_ROOT=C:\Users\issda\SCBE-AETHERMOORE"
set "PS_SCRIPT=%SCBE_ROOT%\skills\clawhub\scbe-colab-n8n-bridge\scripts\activate_colab_runtime.ps1"
set "SCBE_PROFILE=colab_local"
set "SCBE_PORT=8888"
set "SCBE_TOKEN=scbe-local-bridge"
set "SCBE_NOTEBOOK_DIR=C:\Users\issda"
set "SCBE_POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%PS_SCRIPT%" (
    echo Missing runtime activator: %PS_SCRIPT%
    exit /b 1
)

if not exist "%SCBE_POWERSHELL%" (
    echo Missing PowerShell executable.
    exit /b 2
)

start "" "%SCBE_POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%PS_SCRIPT%" -Profile "%SCBE_PROFILE%" -Port %SCBE_PORT% -Token "%SCBE_TOKEN%" -NotebookDir "%SCBE_NOTEBOOK_DIR%"
exit /b 0
