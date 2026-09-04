@echo off
REM === aiZee Sync Script: .ai -> aizee ===
REM Copies all files from the working directory (.ai) to the deployment folder (aizee).
REM Usage: scripts\update_aizee.bat
REM
REM [DIR-01] .ai is the ONLY working directory. aizee is READ-ONLY except via this script.

setlocal enabledelayedexpansion

REM Derive paths relative to this script's location (portable across machines).
REM Source = parent of scripts/ dir (the .ai working directory).
REM Target = sibling "aizee" deployment folder (override via AIZEE_DEPLOY env if needed).
set "SOURCE=%~dp0.."
if defined AIZEE_DEPLOY (set "TARGET=%AIZEE_DEPLOY%") else (set "TARGET=%~dp0..\..\aizee")

echo === aiZee Sync: %SOURCE% -^> %TARGET% ===

if not exist "%TARGET%" (
    echo ERROR: Target directory %TARGET% does not exist.
    exit /b 1
)

REM Sync runtime/ (core modules)
echo Syncing runtime/...
xcopy "%SOURCE%\runtime\*" "%TARGET%\runtime\" /E /I /Y /Q >nul

REM Sync scripts/ (validators + generators)
echo Syncing scripts/...
xcopy "%SOURCE%\scripts\*" "%TARGET%\scripts\" /E /I /Y /Q >nul

REM Sync tests/ (new test files)
echo Syncing tests/...
xcopy "%SOURCE%\tests\*" "%TARGET%\tests\" /E /I /Y /Q >nul

REM Sync tech-stack/ (updated + new references)
echo Syncing tech-stack/...
xcopy "%SOURCE%\tech-stack\*" "%TARGET%\tech-stack\" /E /I /Y /Q >nul

REM Sync skills/ (updated SKILL.md files)
echo Syncing skills/...
xcopy "%SOURCE%\skills\*" "%TARGET%\skills\" /E /I /Y /Q >nul

REM Sync workflows/ (new + updated workflows)
echo Syncing workflows/...
xcopy "%SOURCE%\workflows\*" "%TARGET%\workflows\" /E /I /Y /Q >nul

REM Sync root files
echo Syncing root files...
copy /Y "%SOURCE%\pyproject.toml" "%TARGET%\pyproject.toml" >nul
copy /Y "%SOURCE%\manifest.json" "%TARGET%\manifest.json" >nul
copy /Y "%SOURCE%\Memory.md" "%TARGET%\Memory.md" >nul
copy /Y "%SOURCE%\README.md" "%TARGET%\README.md" >nul
copy /Y "%SOURCE%\README-AR.md" "%TARGET%\README-AR.md" >nul
copy /Y "%SOURCE%\CHANGELOG.md" "%TARGET%\CHANGELOG.md" >nul
copy /Y "%SOURCE%\AGENTS.md" "%TARGET%\AGENTS.md" >nul
copy /Y "%SOURCE%\.aizee-version" "%TARGET%\.aizee-version" >nul
copy /Y "%SOURCE%\.windsurfrules" "%TARGET%\.windsurfrules" >nul
copy /Y "%SOURCE%\config.py" "%TARGET%\config.py" >nul
copy /Y "%SOURCE%\aizee_cli.py" "%TARGET%\aizee_cli.py" >nul

REM Sync .cursor/rules/ (updated rule files)
echo Syncing .cursor/rules/...
if exist "%SOURCE%\.cursor\rules" (
    xcopy "%SOURCE%\.cursor\rules\*" "%TARGET%\.cursor\rules\" /E /I /Y /Q >nul
)

REM Sync .claude/ (MCP server config + permissions)
echo Syncing .claude/...
if exist "%SOURCE%\.claude" (
    xcopy "%SOURCE%\.claude\*" "%TARGET%\.claude\" /E /I /Y /Q >nul
)

REM Sync aizee_mcp/ (MCP server + tools)
echo Syncing aizee_mcp/...
xcopy "%SOURCE%\aizee_mcp\*" "%TARGET%\aizee_mcp\" /E /I /Y /Q >nul

REM Sync memory/ (memory subsystem)
echo Syncing memory/...
xcopy "%SOURCE%\memory\*" "%TARGET%\memory\" /E /I /Y /Q >nul

REM Sync eval/ (evaluation harness)
echo Syncing eval/...
xcopy "%SOURCE%\eval\*" "%TARGET%\eval\" /E /I /Y /Q >nul

REM Sync dashboard/ (web UI server) — previously missing from sync (SYNC fix)
echo Syncing dashboard/...
xcopy "%SOURCE%\dashboard\*" "%TARGET%\dashboard\" /E /I /Y /Q >nul

REM Sync plugins/ (plugin subsystem) — previously missing from sync (SYNC fix)
echo Syncing plugins/...
xcopy "%SOURCE%\plugins\*" "%TARGET%\plugins\" /E /I /Y /Q >nul

REM Sync rules/ (compressed behavioral rules)
echo Syncing rules/...
if exist "%SOURCE%\rules" (
    xcopy "%SOURCE%\rules\*" "%TARGET%\rules\" /E /I /Y /Q >nul
)

REM Sync .devin/ (Devin CLI config + skills)
echo Syncing .devin/...
if exist "%SOURCE%\.devin" (
    xcopy "%SOURCE%\.devin\*" "%TARGET%\.devin\" /E /I /Y /Q >nul
)

REM Sync .github/ (CI/CD workflows)
echo Syncing .github/...
if exist "%SOURCE%\.github" (
    xcopy "%SOURCE%\.github\*" "%TARGET%\.github\" /E /I /Y /Q >nul
)

REM Sync installer/ (GUI installer)
echo Syncing installer/...
if exist "%SOURCE%\installer" (
    xcopy "%SOURCE%\installer\*" "%TARGET%\installer\" /E /I /Y /Q >nul
)

REM Sync additional root files
echo Syncing additional root files...
if exist "%SOURCE%\global-roles.md" copy /Y "%SOURCE%\global-roles.md" "%TARGET%\global-roles.md" >nul
if exist "%SOURCE%\global-workflow.md" copy /Y "%SOURCE%\global-workflow.md" "%TARGET%\global-workflow.md" >nul
if exist "%SOURCE%\.env.example" copy /Y "%SOURCE%\.env.example" "%TARGET%\.env.example" >nul
if exist "%SOURCE%\.gitignore" copy /Y "%SOURCE%\.gitignore" "%TARGET%\.gitignore" >nul
if exist "%SOURCE%\.editorconfig" copy /Y "%SOURCE%\.editorconfig" "%TARGET%\.editorconfig" >nul
if exist "%SOURCE%\.bandit" copy /Y "%SOURCE%\.bandit" "%TARGET%\.bandit" >nul
if exist "%SOURCE%\LICENSE" copy /Y "%SOURCE%\LICENSE" "%TARGET%\LICENSE" >nul
if exist "%SOURCE%\NOTICE" copy /Y "%SOURCE%\NOTICE" "%TARGET%\NOTICE" >nul
if exist "%SOURCE%\CONTRIBUTING.md" copy /Y "%SOURCE%\CONTRIBUTING.md" "%TARGET%\CONTRIBUTING.md" >nul
if exist "%SOURCE%\DESIGN.md" copy /Y "%SOURCE%\DESIGN.md" "%TARGET%\DESIGN.md" >nul

echo.
echo === Sync Complete ===
echo Verify with: cd %TARGET% ^&^& python eval\harness.py
echo.
endlocal
