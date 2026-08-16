@echo off
setlocal
set "WORKSPACE=%CD%"
if not "%~1"=="" set "WORKSPACE=%~1"

call "%~dp0setup_windows.bat"
if errorlevel 1 (
    pause
    exit /b 1
)

echo.
echo [run] Starting XingClaw CLI interactive mode ...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" -Mode cli -Workspace "%WORKSPACE%"
if errorlevel 1 pause
