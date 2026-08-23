@echo off
REM ============================================================
REM  aiZee Installer Launcher (Windows)
REM  Double-click this file — no terminal setup needed.
REM  Launches the GUI installer wizard.
REM ============================================================

setlocal
title aiZee Installer
cd /d "%~dp0"

echo.
echo  ============================================================
echo    aiZee Installer
echo    Launching GUI wizard...
echo  ============================================================
echo.

REM --- Launch the GUI installer with execution policy bypass ---
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0installer\gui_installer.ps1"

REM --- Keep window open if there was an error ---
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ============================================================
    echo   [aiZee] Installer exited with error code %ERRORLEVEL%
    echo   [aiZee] Check the log in state\install-*.log
    echo  ============================================================
    echo.
    pause
)
endlocal
