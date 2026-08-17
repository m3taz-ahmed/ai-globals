@echo off
REM aiZee — Brain Restore Launcher (Windows)
REM Modes:
REM   restore.bat              → auto-merge (smart, from checkpoint)
REM   restore.bat --from PATH  → full restore from specific backup
REM   restore.bat --list       → list available backups
REM   restore.bat --checkpoint → show current checkpoint

cd /d "%~dp0"

if "%~1"=="" (
    REM Default: auto-merge mode
    python scripts\restore_brain.py --auto
) else (
    REM Pass arguments through
    python scripts\restore_brain.py %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [aizee] Restore exited with error code %ERRORLEVEL%
    pause
) else (
    echo.
    echo Restore complete. Press any key to close...
    pause >nul
)
