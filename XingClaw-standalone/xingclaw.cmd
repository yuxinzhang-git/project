@echo off
setlocal EnableExtensions

set "XINGCLAW_DIR=%~dp0"
set "WORKSPACE=%CD%"

if /I "%~1"=="--workspace" (
    if "%~2"=="" (
        echo Workspace argument is missing.
        exit /b 2
    )
    set "WORKSPACE=%~2"
) else if /I "%~1"=="-Workspace" (
    if "%~2"=="" (
        echo Workspace argument is missing.
        exit /b 2
    )
    set "WORKSPACE=%~2"
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%XINGCLAW_DIR%dev.ps1" -Mode cli -Workspace "%WORKSPACE%"
exit /b %ERRORLEVEL%
