#!/bin/bash
# AI 个性化学习平台 - 一键启动脚本 (Mac/Linux)

set -e

echo "============================================"
echo "  AI 个性化学习平台 - 一键启动"
echo "============================================"
echo ""

# 检查 Docker
if ! command -v docker &>/dev/null; then
    echo "[错误] 请先安装 Docker Desktop"
    exit 1
fi
if ! docker info &>/dev/null; then
    echo "[错误] Docker 守护进程未运行，请先启动 Docker"
    exit 1
fi

# 步骤1：启动 Docker 基础设施
echo "[1/3] 启动 PostgreSQL + Redis（Docker 容器）..."
docker-compose up -d

# 等待数据库就绪
echo "[*] 等待数据库就绪..."
until docker-compose exec -T postgres pg_isready -U ailearn -d ai_learning 2>/dev/null; do
  sleep 2
done
echo "[*] 数据库已就绪"

# 步骤2：启动后端
echo "[2/3] 启动后端（uvicorn --reload）..."
cd "$(dirname "$0")/backend"
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt -q
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

sleep 3

# 步骤3：启动前端
echo "[3/3] 启动前端（npm run dev）..."
cd "$(dirname "$0")/frontend"
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================"
echo "  启动完成："
echo ""
echo "  后端地址：http://localhost:8000"
echo "  前端地址：http://localhost:5173"
echo "  API 文档：http://localhost:8000/docs"
echo "============================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待子进程
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
