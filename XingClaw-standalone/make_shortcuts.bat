@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcuts.ps1"
if errorlevel 1 (
    echo [shortcut] Failed to create shortcuts.
    pause
    exit /b 1
)
pause
