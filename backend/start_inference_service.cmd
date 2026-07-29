@echo off
cd /d D:\jay_demo\vae_demo\backend
set HF_HOME=D:\jay_demo\models
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set BGE_MODEL_PATH=D:\jay_demo\models\bge-m3
set BGE_RERANKER_PATH=D:\jay_demo\models\bge-reranker-v2-m3
set BGE_DEVICE=cuda
set BGE_INFERENCE_RUNTIME=torch
D:\jay_demo\bge_env\Scripts\python.exe -m uvicorn inference_service.app:app --host 127.0.0.1 --port 8100
