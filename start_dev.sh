#!/bin/bash
# 开发模式启动（后端+前端同时运行）

echo "=== 启动后端 (FastAPI) ==="
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000 &

echo "=== 启动前端 (Vite) ==="
cd frontend && npm run dev &

echo ""
echo "后端: http://localhost:8000"
echo "前端: http://localhost:3000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "默认管理员: admin / admin123"

wait
