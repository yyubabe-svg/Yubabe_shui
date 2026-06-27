#!/bin/bash
# ============================================
# 蜀水智库 AI - 开发模式启动脚本
# 功能：前后端分离启动，支持热重载
# - 后端：FastAPI + uvicorn --reload (端口 8000)
# - 前端：Vite dev server (端口 5173)
#
# 开发时访问：http://localhost:5173
# ============================================

set -e
cd "$(dirname "$0")"

PROJECT_DIR="$(pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  蜀水智库 AI - 开发模式${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

# ---- 检查Python虚拟环境 ----
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}📦 创建Python虚拟环境...${NC}"
    cd "$BACKEND_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt --break-system-packages -q
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✅ Python环境就绪${NC}"
    echo ""
fi

# ---- 检查前端依赖 ----
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}📦 安装前端依赖...${NC}"
    cd "$FRONTEND_DIR"
    npm install
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✅ 前端依赖就绪${NC}"
    echo ""
fi

# ---- 停止旧进程 ----
echo -e "${YELLOW}🧹 清理旧进程...${NC}"
lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
sleep 1

# ---- 获取局域网IP ----
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

# ---- 启动后端（后台，热重载） ----
echo -e "${GREEN}🚀 启动后端（热重载模式）...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
nohup python -m uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT > /tmp/shushui_backend_dev.log 2>&1 &
BACKEND_PID=$!
cd "$PROJECT_DIR"

sleep 2

# 检查后端
if ! curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
    echo -e "${RED}❌ 后端启动失败，请查看日志: /tmp/shushui_backend_dev.log${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 后端已启动 (PID: $BACKEND_PID, 端口: $BACKEND_PORT)${NC}"

# ---- 启动前端（后台，热重载） ----
echo -e "${BLUE}🚀 启动前端（Vite dev server）...${NC}"
cd "$FRONTEND_DIR"
nohup npm run dev > /tmp/shushui_frontend_dev.log 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_DIR"

sleep 3

# 检查前端
if ! curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  前端可能仍在启动中，请稍等...${NC}"
fi
echo -e "${BLUE}✅ 前端已启动 (PID: $FRONTEND_PID, 端口: $FRONTEND_PORT)${NC}"

# ---- 保存PID ----
echo "$BACKEND_PID $FRONTEND_PID" > /tmp/shushui_dev_pids.txt

# ---- 输出信息 ----
echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}  ✅ 开发环境已启动！${NC}"
echo ""
echo -e "  ${GREEN}前端访问:${NC}    http://localhost:${FRONTEND_PORT}"
echo -e "  ${GREEN}后端API:${NC}     http://localhost:${BACKEND_PORT}"
echo -e "  ${BLUE}API文档:${NC}     http://localhost:${BACKEND_PORT}/docs"
echo ""
echo -e "  ${YELLOW}📌 开发提示:${NC}"
echo -e "  ${YELLOW}  • 修改后端代码自动重载${NC}"
echo -e "  ${YELLOW}  • 修改前端代码自动热更新${NC}"
echo -e "  ${YELLOW}  • 后端日志: tail -f /tmp/shushui_backend_dev.log${NC}"
echo -e "  ${YELLOW}  • 前端日志: tail -f /tmp/shushui_frontend_dev.log${NC}"
echo ""
echo -e "  ${RED}运行 ./stop.sh 停止所有服务${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

# 输出实时日志
echo -e "${BLUE}📋 后端日志（按 Ctrl+C 停止日志查看，服务继续后台运行）:${NC}"
echo ""
tail -f /tmp/shushui_backend_dev.log
