#!/bin/bash
# ============================================
# 蜀水智库 AI - 本地一键启动脚本（推荐日常使用）
# 功能：自动构建前端 + 启动后端（后端托管前端静态文件）
# 访问：http://localhost:8000
#
# 用法：./start.sh [--skip-build]
#   --skip-build   跳过前端构建（使用已有的dist，加快启动速度）
# ============================================

set -e
cd "$(dirname "$0")"

PROJECT_DIR="$(pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
PORT=8000
SKIP_BUILD=false

# 解析参数
for arg in "$@"; do
    case "$arg" in
        --skip-build) SKIP_BUILD=true ;;
    esac
done

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  蜀水智库 AI - 本地启动${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ---- 构建前端 ----
if [ "$SKIP_BUILD" = true ]; then
    echo -e "${YELLOW}⏭️  跳过前端构建（使用已有dist）${NC}"
    if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
        echo -e "${RED}❌ dist目录不存在，无法跳过构建，请去掉 --skip-build 参数${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}📦 检查前端依赖...${NC}"
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 安装前端依赖...${NC}"
        npm install
    fi
    echo -e "${YELLOW}🔨 构建前端生产版本...${NC}"
    npm run build
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✅ 前端构建完成${NC}"
    echo ""
fi

# ---- 检查Python虚拟环境 ----
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}📦 首次运行，创建Python虚拟环境...${NC}"
    cd "$BACKEND_DIR"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${YELLOW}📦 安装Python依赖...${NC}"
    pip install -r requirements.txt --break-system-packages -q
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✅ Python环境就绪${NC}"
    echo ""
fi

# ---- 检查后端依赖是否完整 ----
cd "$BACKEND_DIR"
source venv/bin/activate
python -c "import fastapi, uvicorn" 2>/dev/null || {
    echo -e "${YELLOW}📦 补装Python依赖...${NC}"
    pip install -r requirements.txt --break-system-packages -q
}
cd "$PROJECT_DIR"

# ---- 检查端口占用 ----
if lsof -ti :$PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  端口 $PORT 已被占用，正在停止旧进程...${NC}"
    lsof -ti :$PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

# ---- 获取局域网IP ----
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

# ---- 启动后端 ----
echo -e "${GREEN}🚀 启动后端服务...${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ 蜀水智库 AI 已启动！${NC}"
echo ""
echo -e "  ${GREEN}本机访问:${NC}   http://localhost:${PORT}"
echo -e "  ${GREEN}局域网访问:${NC} http://${LOCAL_IP}:${PORT}"
echo ""
echo -e "  ${BLUE}API文档:${NC}   http://localhost:${PORT}/docs"
echo ""
echo -e "  ${YELLOW}按 Ctrl+C 停止服务${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

cd "$BACKEND_DIR"
source venv/bin/activate
exec python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
