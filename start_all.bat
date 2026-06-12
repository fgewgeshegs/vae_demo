@echo off
echo Starting Backend...
start /B /MIN "" "D:\jay_demo\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000 > "D:\jay_demo\backend\uvicorn_start.log" 2>&1
echo PID: %ERRORLEVEL%
echo Backend started on port 8000
echo.
echo Starting Frontend...
start /B /MIN "" cmd /c "cd /d D:\jay_demo\frontend && npx.cmd vite --port 5173" > "D:\jay_demo\frontend\vite_start.log" 2>&1
echo PID: %ERRORLEVEL%
echo Frontend started on port 5173
echo.
echo Done! Both services are starting up.
