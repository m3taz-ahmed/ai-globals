@echo off
REM aiZee — GUI Uninstaller Launcher (Windows)
REM Launches the tkinter GUI uninstaller with selective keep/backup.
REM No terminal needed — just double-click this file.

cd /d "%~dp0"

REM Try GUI mode first, fall back to console if tkinter unavailable
python runtime\uninstaller_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [aizee] GUI unavailable. Launching console uninstaller...
    echo.
    python -m aizee_cli uninstall
    pause
)
