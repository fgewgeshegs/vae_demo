@echo off
cd /d D:\jay_demo\backend
start /B /MIN "" "D:\jay_demo\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000 > startup2.log 2>&1
