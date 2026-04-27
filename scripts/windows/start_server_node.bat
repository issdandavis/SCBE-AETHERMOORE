@echo off
REM Start SCBE Server Node on Windows
REM Double-click this or add to Task Scheduler for auto-start

cd /d "%~dp0\..\.."
echo Starting SCBE Server Node...
python scripts\server_node.py %*
pause
