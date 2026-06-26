@echo off
REM Launches the installed AetherBrowser with automation enabled, so Playwright
REM (or an AI agent) can attach and drive it. Closing this window does not close
REM the browser. The automation port is bound to 127.0.0.1 (this PC only).

set AETHER_AUTOMATION=1
set AETHER_AUTOMATION_PORT=9222

set "APP=%LOCALAPPDATA%\Programs\AetherBrowser\AetherBrowser.exe"
if exist "%APP%" (
  start "" "%APP%"
) else (
  echo Could not find AetherBrowser at:
  echo   %APP%
  echo Install AetherBrowser first, or edit this file's APP path.
  pause
)
