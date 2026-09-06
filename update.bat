@echo off
REM aiZee — Update Launcher (Windows)
REM Pulls latest from GitHub and re-runs post-install hooks.
REM Learned data (memory/state/brain/.env) is preserved.

cd /d "%~dp0"

python scripts\update.py %*
set EXITCODE=%ERRORLEVEL%

echo.
echo ============================================================
if %EXITCODE% EQU 0 (
    echo  [OK] aiZee updated successfully.
) else if %EXITCODE% EQU 2 (
    echo  [DONE] aiZee updated with warnings — check output above.
) else (
    echo  [ERROR] Update exited with error code %EXITCODE%
)
echo ============================================================
echo.

REM Check if GUI installer should be run (first install or missing .aizee-version)
if not exist ".aizee-version" (
    echo  [HINT] No .aizee-version found — this may be a fresh clone.
    echo         To install with the GUI wizard, run: install.bat
    echo         To install silently, run: powershell -ExecutionPolicy Bypass -File installer\gui_installer.ps1 -Silent
    echo.
)

REM Check if .env is missing but .env.example exists (secrets needed)
if not exist ".env" (
    if exist ".env.example" (
        echo  [HINT] .env file not found but .env.example exists.
        echo         To set up MCP credentials, run the GUI installer: install.bat
        echo         Or manually: copy .env.example .env  then edit .env
        echo.
    )
)

REM Check if AIZEE_ROOT is not set
if "%AIZEE_ROOT%"=="" (
    echo  [HINT] AIZEE_ROOT environment variable is not set.
    echo         The GUI installer sets this automatically: install.bat
    echo         Or set it manually: setx AIZEE_ROOT "%CD%"
    echo.
)

echo  Press any key to close this window...
pause >nul
exit /b %EXITCODE%
