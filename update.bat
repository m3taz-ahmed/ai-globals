@echo off
REM aiZee — Update Launcher (Windows)
REM Pulls latest from GitHub and re-runs post-install hooks.
REM Learned data (memory/state/brain/.env) is preserved.

cd /d "%~dp0"

python scripts\update.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [aizee] Update exited with error code %ERRORLEVEL%
    pause
)
