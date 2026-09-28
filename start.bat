@echo off
cd /d "%~dp0"
set "PORT_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do set "PORT_PID=%%P"
if defined PORT_PID (
    curl.exe -fsS http://127.0.0.1:8000/api/status 2>nul | findstr /C:"2.2.0" >nul
    if errorlevel 1 (
        echo Port 8000 is already used by another service. Close it before starting my-agent.
        pause
        exit /b 1
    )

    curl.exe -fsS http://127.0.0.1:8000/sports.html 2>nul | findstr /C:"/api/sports/asian-games" >nul
    if not errorlevel 1 (
        curl.exe -fsS -D - http://127.0.0.1:8000/sports.html -o NUL 2>nul | findstr /I /C:"no-store" >nul
        if not errorlevel 1 (
            echo my-agent is already running at http://127.0.0.1:8000
            start "" http://127.0.0.1:8000/daily.html
            exit /b 0
        )
    )

    echo An older my-agent instance is serving port 8000. Restarting it...
    taskkill /PID %PORT_PID% /F >nul
    timeout /t 1 /nobreak >nul
)
agent\Scripts\python.exe agent_api.py
