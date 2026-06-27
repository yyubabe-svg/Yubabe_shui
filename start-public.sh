#!/bin/bash
# ============================================
# 蜀水智库 AI - 公网发布一键启动脚本
# 功能：自动构建前端 + 启动后端 + Cloudflare Tunnel 公网穿透
# 用途：让同事/外部用户通过公网访问
#
# 用法：./start-public.sh [--skip-build]
#   --skip-build   跳过前端构建（使用已有的dist，加快启动速度）
#
# 注意：
# 1. 每次启动会获得新的公网地址
# 2. 需要保持电脑开机和终端运行
# 3. 启动后会自动更新 backend/.env 中的公网地址配置
# ============================================

set -e
cd "$(dirname "$0")"

PROJECT_DIR="$(pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
PORT=8000
TUNNEL_LOG="/tmp/cloudflared_shushui.log"
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
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  蜀水智库 AI - 公网发布模式${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ---- 检查 cloudflared ----
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}📦 正在安装 cloudflared（公网穿透工具）...${NC}"
    if command -v brew &> /dev/null; then
        brew install cloudflared
    else
        echo -e "${RED}❌ 请先安装 Homebrew: https://brew.sh${NC}"
        echo -e "${RED}   或手动安装 cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ cloudflared 安装完成${NC}"
    echo ""
fi

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
    echo -e "${YELLOW}📦 创建Python虚拟环境...${NC}"
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
# 快速检查关键依赖是否安装
python -c "import fastapi, uvicorn" 2>/dev/null || {
    echo -e "${YELLOW}📦 补装Python依赖...${NC}"
    pip install -r requirements.txt --break-system-packages -q
}
cd "$PROJECT_DIR"

# ---- 停止旧进程 ----
echo -e "${YELLOW}🧹 清理旧进程...${NC}"
lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
pkill -f "cloudflared tunnel.*:$PORT" 2>/dev/null || true
pkill -f "cloudflared.*8000" 2>/dev/null || true
sleep 2

# ---- 获取局域网IP ----
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

# ---- 启动后端（后台） ----
echo -e "${GREEN}🚀 启动后端服务...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT > /tmp/shushui_backend.log 2>&1 &
BACKEND_PID=$!
cd "$PROJECT_DIR"

sleep 3

# 检查后端是否启动成功
if ! curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo -e "${RED}❌ 后端启动失败！查看日志:${NC}"
    tail -20 /tmp/shushui_backend.log
    exit 1
fi
echo -e "${GREEN}✅ 后端已启动 (PID: $BACKEND_PID)${NC}"

# 验证前端静态文件可访问
if curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/ | grep -q "200"; then
    echo -e "${GREEN}✅ 前端页面可正常访问${NC}"
else
    echo -e "${YELLOW}⚠️  前端页面访问异常，检查构建是否正确${NC}"
fi

# ---- 启动 Cloudflare Tunnel ----
echo -e "${GREEN}🌐 启动公网隧道...${NC}"
echo ""

# 启动隧道并捕获输出
rm -f "$TUNNEL_LOG"
nohup cloudflared tunnel --url http://localhost:$PORT --no-autoupdate > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# 等待隧道建立（最多30秒）
echo -e "${YELLOW}⏳ 等待公网隧道建立...${NC}"
PUBLIC_URL=""
for i in {1..30}; do
    sleep 1
    if grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" "$TUNNEL_LOG" | head -1 | grep -q "https"; then
        PUBLIC_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" "$TUNNEL_LOG" | head -1)
        break
    fi
done

if [ -z "$PUBLIC_URL" ]; then
    echo -e "${RED}❌ 公网隧道建立失败，请检查日志: $TUNNEL_LOG${NC}"
    tail -20 "$TUNNEL_LOG"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# ---- 更新 .env 中的公网地址（用于支付宝回调等） ----
cd "$BACKEND_DIR"
touch .env
# 更新 SERVER_PUBLIC_URL
if grep -q "SERVER_PUBLIC_URL=" .env; then
    sed -i '' "s|SERVER_PUBLIC_URL=.*|SERVER_PUBLIC_URL=$PUBLIC_URL|g" .env
else
    echo "SERVER_PUBLIC_URL=$PUBLIC_URL" >> .env
fi
# 更新 ALIPAY_NOTIFY_URL
if grep -q "ALIPAY_NOTIFY_URL=" .env; then
    sed -i '' "s|ALIPAY_NOTIFY_URL=.*|ALIPAY_NOTIFY_URL=$PUBLIC_URL/api/payment/alipay/notify|g" .env
else
    echo "ALIPAY_NOTIFY_URL=$PUBLIC_URL/api/payment/alipay/notify" >> .env
fi
# 更新 ALIPAY_RETURN_URL
if grep -q "ALIPAY_RETURN_URL=" .env; then
    sed -i '' "s|ALIPAY_RETURN_URL=.*|ALIPAY_RETURN_URL=$PUBLIC_URL/api/payment/return|g" .env
else
    echo "ALIPAY_RETURN_URL=$PUBLIC_URL/api/payment/return" >> .env
fi
cd "$PROJECT_DIR"

# ---- 重启后端以加载新的.env配置 ----
echo -e "${YELLOW}🔄 重启后端以加载公网配置...${NC}"
kill $BACKEND_PID 2>/dev/null
sleep 1
cd "$BACKEND_DIR"
source venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT > /tmp/shushui_backend.log 2>&1 &
BACKEND_PID=$!
cd "$PROJECT_DIR"
sleep 2

if ! curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo -e "${RED}❌ 后端重启失败${NC}"
    exit 1
fi

# ---- 输出访问信息 ----
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ 蜀水智库 AI 公网发布成功！${NC}"
echo ""
echo -e "  ${GREEN}本机访问:${NC}    http://localhost:${PORT}"
echo -e "  ${GREEN}局域网访问:${NC}  http://${LOCAL_IP}:${PORT}"
echo -e "  ${CYAN}🌐 公网访问:${NC}   $PUBLIC_URL"
echo ""
echo -e "  ${BLUE}API文档:${NC}    $PUBLIC_URL/docs"
echo ""
echo -e "  ${YELLOW}📌 重要提示:${NC}"
echo -e "  ${YELLOW}  • 请保持此终端窗口打开${NC}"
echo -e "  ${YELLOW}  • 电脑需保持开机状态${NC}"
echo -e "  ${YELLOW}  • 每次重启此脚本会获得新的公网地址${NC}"
echo -e "  ${YELLOW}  • 后端日志: tail -f /tmp/shushui_backend.log${NC}"
echo -e "  ${YELLOW}  • 隧道日志: tail -f $TUNNEL_LOG${NC}"
echo ""
echo -e "  ${RED}按 Ctrl+C 停止所有服务${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 保存PID到文件
echo "$BACKEND_PID $TUNNEL_PID" > /tmp/shushui_pids.txt

# 等待用户中断
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 正在停止服务...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $TUNNEL_PID 2>/dev/null || true
    pkill -f "cloudflared.*8000" 2>/dev/null || true
    lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✅ 服务已停止${NC}"
    exit 0
}

trap cleanup INT TERM

# 保持运行并输出后端日志
tail -f /tmp/shushui_backend.log
