@echo off
setlocal
cd /d "%~dp0"

set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if exist "%VENV_PY%" goto install

where py >nul 2>&1
if not errorlevel 1 (
    echo [setup] Creating virtual environment with py -3 ...
    py -3 -m venv "%VENV_DIR%"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [setup] ERROR: Python 3.10+ was not found in PATH.
        echo [setup] Install Python from https://www.python.org/downloads/windows/
        exit /b 1
    )
    echo [setup] Creating virtual environment with python ...
    python -m venv "%VENV_DIR%"
)
if errorlevel 1 (
    echo [setup] ERROR: Failed to create the virtual environment.
    exit /b 1
)

:install
echo [setup] Installing XingClaw and its dependencies ...
"%VENV_PY%" -m pip install -e ".[dev]"
if errorlevel 1 (
    echo [setup] ERROR: Dependency installation failed. Check network access and try again.
    exit /b 1
)

if not exist "%~dp0.env.ps1" (
    copy /Y "%~dp0.env.ps1.example" "%~dp0.env.ps1" >nul
    echo [setup] Created .env.ps1 from .env.ps1.example.
    echo [setup] Edit .env.ps1 and fill in your model API key before starting.
)

echo [setup] Ready.
exit /b 0
