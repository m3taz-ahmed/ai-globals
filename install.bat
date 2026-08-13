@echo off
REM AI Global OS — Double-click GUI Installer Launcher (Windows)
REM No terminal needed — just double-click this file.

REM Change to the directory where this .bat lives
cd /d "%~dp0"

REM Launch the GUI installer with execution policy bypass
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0installer\gui_installer.ps1"

REM Keep window open if there was an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [aios] Installer exited with error code %ERRORLEVEL%
    echo [aios] Check the log in state\install-*.log
    pause
)
