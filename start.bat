@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   E-commerce Agent SaaS - Startup
echo ============================================

:: Set model path
set M3E_MODEL_PATH=C:\Users\Administrator\PyCharmMiscProject\m3e-base

:: Find available port (skip 8000 which has zombie)
set PORT=0
for /L %%p in (8001,1,8009) do (
    netstat -ano | findstr ":%%p " | findstr "LISTENING" >nul 2>&1
    if errorlevel 1 (
        if %PORT%==0 set PORT=%%p
    )
)
echo Backend port: %PORT%
set BACKEND_URL=http://localhost:%PORT%

:: Start backend in a new window
echo Starting backend...
start "Agent-SaaS-Backend" cmd /c "cd /d "%~dp0backend" && set M3E_MODEL_PATH=%M3E_MODEL_PATH% && python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%"

:: Wait for backend (Python one-liner, works on all Windows)
echo Waiting for backend to be ready...
:waitloop
timeout /t 3 /nobreak >nul
python -c "import urllib.request; urllib.request.urlopen('http://localhost:%PORT%/api/health')" >nul 2>&1
if errorlevel 1 goto waitloop
echo Backend is ready!

:: Start frontend in a new window
echo Starting frontend...
cd /d "%~dp0frontend"
start "Agent-SaaS-Frontend" cmd /c "set BACKEND_URL=%BACKEND_URL% && streamlit run app.py"

echo.
echo ============================================
echo   Done! Visit: http://localhost:8501
echo   Backend API docs: http://localhost:%PORT%/docs
echo ============================================
echo.
echo Close the backend/frontend windows and press any key here to exit.
pause >nul
