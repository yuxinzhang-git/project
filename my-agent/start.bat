@echo off
cd /d "%~dp0"
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if not errorlevel 1 (
    echo my-agent is already running at http://127.0.0.1:8000
    echo Close its command window or press Ctrl+C there before starting again.
    pause
    exit /b 0
)
agent\Scripts\python.exe agent_api.py
