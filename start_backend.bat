@echo off
cd /d D:\jay_demo\backend
D:\jay_demo\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --host 0.0.0.0 > D:\jay_demo\backend\uvicorn.log 2>&1
