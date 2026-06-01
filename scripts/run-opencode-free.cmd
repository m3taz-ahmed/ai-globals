@echo off
title OpenCode (Free Keys Launcher)
echo Launching OpenCode Free Keys Launcher...
powershell -NoProfile -ExecutionPolicy Bypass -File "d:\server\.ai\scripts\run-opencode-free.ps1"
if %errorlevel% neq 0 (
    echo.
    echo Something went wrong. Press any key to exit...
    pause > nul
)
