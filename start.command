#!/bin/bash
# 蜀水智库 AI - 一键启动脚本 (Mac/Linux)
# 双击此文件即可启动前后端服务

cd "$(dirname "$0")"

echo "========================================="
echo "  蜀水智库 AI - 启动中..."
echo "========================================="
echo ""

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3，请先安装 Python 3.10+${NC}"
    echo "下载地址: https://www.python.org/downloads/"
    read -p "按回车退出..."
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未找到 node，请先安装 Node.js 18+${NC}"
    echo "下载地址: https://nodejs.org/"
    read -p "按回车退出..."
    exit 1
fi

echo -e "${GREEN}✓ Python 和 Node.js 环境检查通过${NC}"
echo ""

# 启动后端
echo "📦 启动后端服务 (端口 8000)..."
cd backend
if [ ! -d "venv" ]; then
    echo "  首次运行，创建 Python 虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt --break-system-packages 2>/dev/null || pip install -q -r requirements.txt
echo -e "${GREEN}✓ 后端依赖已就绪${NC}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

sleep 2

# 启动前端
echo ""
echo "🌐 启动前端服务 (端口 5173)..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "  首次运行，安装前端依赖..."
    npm install --silent
fi
echo -e "${GREEN}✓ 前端依赖已就绪${NC}"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo -e "${GREEN}  🚀 蜀水智库 AI 启动成功！${NC}"
echo "========================================="
echo ""
echo "  📱 前端地址: http://localhost:5173"
echo "  🔧 后端API:  http://localhost:8000"
echo "  📖 API文档:  http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}  提示: 关闭此窗口即可停止所有服务${NC}"
echo "========================================="
echo ""

# 等待用户中断
trap "echo ''; echo '正在关闭服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '已关闭，再见！'; exit 0" INT
wait
