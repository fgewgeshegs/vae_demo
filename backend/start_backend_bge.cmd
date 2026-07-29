@echo off
cd /d D:\jay_demo\vae_demo\backend
set HF_HOME=D:\jay_demo\models
set HF_HUB_CACHE=D:\jay_demo\models\hub
set HF_XET_CACHE=D:\jay_demo\models\xet
set TEMP=D:\jay_demo\models\tmp
set TMP=D:\jay_demo\models\tmp
D:\jay_demo\bge_env\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
