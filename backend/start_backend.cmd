@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log >> "%~dp0uvicorn.log" 2>&1
