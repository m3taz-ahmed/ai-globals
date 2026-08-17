@echo off
REM aiZee — Brain Backup Launcher (Windows)
REM Backs up learned data (memory/state/brain/graphify-out/.env) to a timestamped folder.

cd /d "%~dp0"

python scripts\backup_brain.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [aizee] Backup exited with error code %ERRORLEVEL%
    pause
) else (
    echo.
    echo Backup complete. Press any key to close...
    pause >nul
)
