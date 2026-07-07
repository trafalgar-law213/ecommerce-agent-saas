@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 自动检测 m3e-base 模型路径
set "M3E_MODEL_PATH="
if exist "%~dp0..\m3e-base" (
    echo [OK] Found local m3e-base model
    set "M3E_MODEL_PATH=%~dp0..\m3e-base"
) else if exist "C:\Users\Administrator\PyCharmMiscProject\m3e-base" (
    echo [OK] Found m3e-base model in PyCharm project
    set "M3E_MODEL_PATH=C:\Users\Administrator\PyCharmMiscProject\m3e-base"
) else (
    echo [INFO] No local m3e-base found, will download from HuggingFace mirror on first use ^(about 430MB^)
)

echo ============================================
echo   E-commerce Agent SaaS - Startup
echo ============================================
echo.
echo Backend:  http://localhost:8001
echo Frontend: http://localhost:8501
echo.

echo Step 1/3: Starting backend...
if "%M3E_MODEL_PATH%"=="" (
    start "Backend" /D "%~dp0backend" cmd /k "title Backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
) else (
    start "Backend" /D "%~dp0backend" cmd /k "title Backend && set M3E_MODEL_PATH=%M3E_MODEL_PATH% && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
)

echo Step 2/3: Waiting for backend...
:wait
timeout /t 2 /nobreak >nul
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/health')" >nul 2>&1
if errorlevel 1 goto wait
echo Backend is ready!

echo Step 3/3: Starting frontend...
start "Frontend" /D "%~dp0frontend" cmd /k "title Frontend && set BACKEND_URL=http://localhost:8001 && streamlit run app.py"

echo.
echo ============================================
echo   Done! Open http://localhost:8501
echo ============================================
pause
