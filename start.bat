@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PORT=8001
set M3E_MODEL_PATH=C:\Users\Administrator\PyCharmMiscProject\m3e-base

echo ============================================
echo   E-commerce Agent SaaS - Startup
echo ============================================
echo.
echo Backend:  http://localhost:%PORT%
echo Frontend: http://localhost:8501
echo.

echo Step 1/2: Starting backend...
start "Backend" /D "%~dp0backend" cmd /k "set M3E_MODEL_PATH=%M3E_MODEL_PATH% && python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%"

echo Step 2/2: Waiting for backend...
:wait
timeout /t 2 /nobreak >nul
python -c "import urllib.request; urllib.request.urlopen('http://localhost:%PORT%/api/health')" >nul 2>&1
if errorlevel 1 goto wait
echo Backend is ready!

echo Step 3/3: Starting frontend...
start "Frontend" /D "%~dp0frontend" cmd /k "set BACKEND_URL=http://localhost:%PORT% && streamlit run app.py"

echo.
echo ============================================
echo   Done! Open http://localhost:8501
echo ============================================
pause
