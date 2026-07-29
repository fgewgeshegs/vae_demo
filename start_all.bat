@echo off
set "ROOT=%~dp0"
set "BGE_PYTHON=D:\jay_demo\bge_env\Scripts\python.exe"
if not exist "%BGE_PYTHON%" (
    echo ERROR: BGE Python not found at %BGE_PYTHON%
    echo Install the BGE environment per ENVIRONMENT.md or update BGE_PYTHON in this script.
    exit /b 1
)
echo Starting Backend...
pushd "%ROOT%backend"
start "" /MIN "%BGE_PYTHON%" -m uvicorn app.main:app --port 8000 > "%ROOT%backend\uvicorn_start.log" 2>&1
popd
echo PID: %ERRORLEVEL%
echo Backend started on port 8000
echo.
echo Starting Frontend...
pushd "%ROOT%frontend"
start "" /MIN npx.cmd vite --port 5173 > "%ROOT%frontend\vite_start.log" 2>&1
popd
echo PID: %ERRORLEVEL%
echo Frontend started on port 5173
echo.
echo Done! Both services are starting up.
