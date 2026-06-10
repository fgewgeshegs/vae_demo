@echo off
chcp 65001 >nul
title AI 个性化学习平台 - 启动脚本

echo ============================================
echo   AI 个性化学习平台 - 一键启动
echo ============================================
echo.

:: 检查 Docker
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 请先安装 Docker Desktop
    pause
    exit /b 1
)
docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] Docker 守护进程未运行，请先启动 Docker Desktop
    pause
    exit /b 1
)

:: 步骤1：启动 Docker 基础设施
echo [1/3] 启动 PostgreSQL + Redis（Docker 容器）...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [错误] Docker 启动失败，请确认 Docker Desktop 已安装并运行
    pause
    exit /b 1
)

:: 等待数据库就绪
echo [*] 等待数据库就绪...
:wait_db
docker-compose exec -T postgres pg_isready -U ailearn -d ai_learning >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 /nobreak >nul
    goto wait_db
)
echo [*] 数据库已就绪

:: 步骤2：启动后端
echo [2/3] 启动后端（uvicorn --reload）...
start "Backend" cmd /c "cd /d %~dp0backend && python -m venv .venv 2>nul && call .venv\Scripts\activate.bat && pip install -r requirements.txt -q && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 步骤3：启动前端
echo [3/3] 启动前端（npm run dev）...
start "Frontend" cmd /c "cd /d %~dp0frontend && npm install && npm run dev"

echo.
echo ============================================
echo   启动完成：
echo.
echo   后端地址：http://localhost:8000
echo   前端地址：http://localhost:5173
echo   API 文档：http://localhost:8000/docs
echo ============================================
echo.
echo 按任意键关闭本窗口（后端和前端将继续运行）
pause >nul
