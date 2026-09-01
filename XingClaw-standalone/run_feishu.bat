@echo off
setlocal
cd /d "%~dp0"

call "%~dp0setup_windows.bat"
if errorlevel 1 (
    pause
    exit /b 1
)

echo.
echo [run] Starting XingClaw Feishu long-connection mode ...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" -Mode im -Transport longconn -Workspace "%~dp0"
if errorlevel 1 pause
