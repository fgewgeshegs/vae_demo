@echo off
cd /d D:\jay_demo\vae_demo\backend
start "Backend" /MIN "D:\jay_demo\bge_env\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
