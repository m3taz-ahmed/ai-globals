@echo off
REM ============================================================
REM  aiZee Dashboard Launcher
REM  Starts the dashboard server and opens the browser automatically.
REM  Double-click this file — no terminal setup needed.
REM ============================================================

setlocal enabledelayedexpansion
title aiZee Dashboard
cd /d "%~dp0"

REM --- Pick a port (first arg or default 8080) ---
set "PORT=8080"
if not "%~1"=="" set "PORT=%~1"

REM --- Find Python ---
set "PYCMD="
for %%c in (python py python3) do (
    where %%c >nul 2>nul && (
        set "PYCMD=%%c"
        goto :found_py
    )
)
echo [aiZee] ERROR: Python not found on PATH.
echo [aiZee] Install Python 3.10+ from https://python.org and try again.
pause
exit /b 1

:found_py
echo.
echo  ============================================================
echo    aiZee Dashboard
echo    Starting server on http://127.0.0.1:%PORT% ...
echo  ============================================================
echo.

REM --- Start the server in a background process ---
start "aiZee Dashboard Server" /min "%PYCMD%" "%~dp0dashboard\server.py" %PORT%

REM --- Wait for the server to be ready (max ~15 seconds) ---
set /a tries=0
:wait_loop
set /a tries+=1
if %tries% gtr 15 (
    echo [aiZee] Server did not start within 15 seconds.
    echo [aiZee] Check for errors above or try a different port.
    pause
    exit /b 1
)
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT%/api/health' -UseBasicParsing -TimeoutSec 2).StatusCode } catch { exit 1 }" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    timeout /t 1 /nobreak >nul
    goto :wait_loop
)

REM --- Server is ready — open the browser ---
echo [aiZee] Server is ready. Opening browser...
start "" "http://127.0.0.1:%PORT%"

echo.
echo  ============================================================
echo   Dashboard is running at http://127.0.0.1:%PORT%
echo   Close this window to keep it running in the background.
echo   To stop: close the "aiZee Dashboard Server" window
echo   or press Ctrl+C in that window.
echo  ============================================================
echo.
echo Press any key to exit this launcher (server stays running)...
pause >nul
endlocal
