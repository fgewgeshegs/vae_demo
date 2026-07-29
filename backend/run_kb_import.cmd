@echo off
cd /d D:\jay_demo\vae_demo\backend
set HF_HOME=D:\jay_demo\models
set HF_HUB_CACHE=D:\jay_demo\models\hub
echo [%date% %time%] Import started > import_final.log
D:\jay_demo\bge_env\Scripts\python.exe -m knowledge_base.import_local_kb >> import_final.log 2>&1
echo [%date% %time%] Import exit code: %ERRORLEVEL% >> import_final.log
