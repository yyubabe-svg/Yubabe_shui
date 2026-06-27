#!/bin/bash
# ============================================
# 蜀水智库 AI - 停止所有服务脚本
# ============================================

cd "$(dirname "$0")"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}🛑 正在停止蜀水智库 AI 所有服务...${NC}"
echo ""

# 停止后端（端口 8000）
if lsof -ti :8000 > /dev/null 2>&1; then
    echo -e "${YELLOW}  停止后端服务 (端口 8000)...${NC}"
    lsof -ti :8000 | xargs kill -9 2>/dev/null
    echo -e "${GREEN}  ✅ 后端已停止${NC}"
else
    echo -e "  后端未运行"
fi

# 停止前端开发服务器（端口 5173）
if lsof -ti :5173 > /dev/null 2>&1; then
    echo -e "${YELLOW}  停止前端开发服务 (端口 5173)...${NC}"
    lsof -ti :5173 | xargs kill -9 2>/dev/null
    echo -e "${GREEN}  ✅ 前端已停止${NC}"
else
    echo -e "  前端开发服务未运行"
fi

# 停止 cloudflared 隧道
if pgrep -f "cloudflared.*8000" > /dev/null 2>&1; then
    echo -e "${YELLOW}  停止 Cloudflare 隧道...${NC}"
    pkill -f "cloudflared.*8000" 2>/dev/null
    echo -e "${GREEN}  ✅ 隧道已停止${NC}"
else
    echo -e "  隧道未运行"
fi

# 清理PID文件
rm -f /tmp/shushui_pids.txt /tmp/shushui_dev_pids.txt

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ 所有服务已停止${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
