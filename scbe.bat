@echo off
REM SCBE-AETHERMOORE Unified Launcher
REM Usage: scbe.bat [cli|agent|demo|memory]

if "%1"=="cli" (
    python scbe-cli.py
) else if "%1"=="agent" (
    python scbe-agent.py
) else if "%1"=="demo" (
    python demo-cli.py
) else if "%1"=="memory" (
    python demo_memory_shard.py
) else (
    echo SCBE-AETHERMOORE v3.0.0
    echo.
    echo Usage: scbe.bat [command]
    echo.
    echo Commands:
    echo   cli      - Interactive CLI with tutorial
    echo   agent    - AI coding assistant
    echo   demo     - Encryption demo
    echo   memory   - AI memory shard demo (60-second story)
    echo.
    echo Examples:
    echo   scbe.bat cli
    echo   scbe.bat agent
    echo   scbe.bat demo
    echo   scbe.bat memory
)
