#!/bin/bash
# ============================================
# 蜀水智库 AI - 管理工具脚本
# 用法: ./manage.sh <命令>
# ============================================

set -e
cd "$(dirname "$0")"

PROJECT_DIR="$(pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

show_help() {
    echo ""
    echo -e "${CYAN}蜀水智库 AI - 管理工具${NC}"
    echo ""
    echo "用法: ./manage.sh <命令>"
    echo ""
    echo "命令列表:"
    echo ""
    echo -e "  ${GREEN}启动/停止:${NC}"
    echo "    start              本地启动（推荐日常使用，自动构建前端+启动后端）"
    echo "    dev                开发模式启动（前后端热重载）"
    echo "    public             公网发布启动（自动构建前端+启动后端+Cloudflare隧道）"
    echo "    stop               停止所有服务"
    echo "    status             查看服务运行状态"
    echo ""
    echo -e "  ${GREEN}启动参数:${NC}"
    echo "    start --skip-build       跳过前端构建，使用已有dist（启动更快）"
    echo "    public --skip-build      跳过前端构建，使用已有dist"
    echo ""
    echo -e "  ${GREEN}构建/部署:${NC}"
    echo "    build              构建前端生产版本"
    echo "    rebuild            重新构建前端并重启后端"
    echo ""
    echo -e "  ${GREEN}激活码管理:${NC}"
    echo "    code:month N [备注]   生成N个月卡激活码"
    echo "    code:year N [备注]    生成N个年卡激活码"
    echo "    code:list             查看所有激活码"
    echo ""
    echo -e "  ${GREEN}系统维护:${NC}"
    echo "    logs               查看后端日志"
    echo "    rebuild-db         重建知识库向量索引"
    echo "    shell              进入后端Python虚拟环境"
    echo ""
    echo -e "  ${GREEN}其他:${NC}"
    echo "    help               显示此帮助"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo "  ./manage.sh start              # 本地启动（自动构建前端）"
    echo "  ./manage.sh start --skip-build # 本地启动（跳过构建，快速启动）"
    echo "  ./manage.sh public             # 公网发布（自动构建+隧道穿透）"
    echo "  ./manage.sh stop               # 停止服务"
    echo "  ./manage.sh code:month 5 推广   # 生成5个月卡"
    echo ""
}

cmd_start() {
    exec ./start.sh "$@"
}

cmd_dev() {
    exec ./start-dev.sh
}

cmd_public() {
    exec ./start-public.sh "$@"
}

cmd_stop() {
    exec ./stop.sh
}

cmd_status() {
    echo ""
    echo -e "${CYAN}📊 服务状态检查${NC}"
    echo ""
    
    # 检查后端
    if lsof -ti :8000 > /dev/null 2>&1; then
        BACKEND_PID=$(lsof -ti :8000 | head -1)
        echo -e "  后端 (端口8000): ${GREEN}✅ 运行中${NC} (PID: $BACKEND_PID)"
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            HEALTH=$(curl -s http://localhost:8000/health)
            echo -e "                  健康检查: ${GREEN}正常${NC}"
        fi
    else
        echo -e "  后端 (端口8000): ${RED}❌ 未运行${NC}"
    fi
    
    # 检查前端开发服务器
    if lsof -ti :5173 > /dev/null 2>&1; then
        FRONTEND_PID=$(lsof -ti :5173 | head -1)
        echo -e "  前端 (端口5173): ${GREEN}✅ 运行中${NC} (PID: $FRONTEND_PID, 开发模式)"
    else
        echo -e "  前端 (端口5173): ${YELLOW}⚠️  开发服务未运行${NC}（生产模式由后端托管）"
    fi
    
    # 检查cloudflared
    if pgrep -f "cloudflared.*8000" > /dev/null 2>&1; then
        CF_PID=$(pgrep -f "cloudflared.*8000" | head -1)
        echo -e "  Cloudflare隧道: ${GREEN}✅ 运行中${NC} (PID: $CF_PID)"
        # 尝试获取公网URL
        PUBLIC_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" /tmp/cloudflared_shushui.log 2>/dev/null | head -1)
        if [ -n "$PUBLIC_URL" ]; then
            echo -e "  公网地址: ${CYAN}$PUBLIC_URL${NC}"
        fi
    else
        echo -e "  Cloudflare隧道: ${YELLOW}未运行${NC}"
    fi
    
    echo ""
}

cmd_build() {
    echo -e "${YELLOW}📦 构建前端...${NC}"
    cd "$FRONTEND_DIR"
    npm run build
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✅ 前端构建完成${NC}"
}

cmd_rebuild() {
    cmd_stop
    sleep 1
    cmd_build
    echo -e "${YELLOW}🚀 重新启动服务...${NC}"
    sleep 1
    exec ./start.sh
}

cmd_code_month() {
    COUNT=${2:-1}
    REMARK="${3:-手动生成}"
    cd "$BACKEND_DIR"
    source venv/bin/activate
    python -m app.tools.admin generate-code --type month --count "$COUNT" --remark "$REMARK"
    cd "$PROJECT_DIR"
}

cmd_code_year() {
    COUNT=${2:-1}
    REMARK="${3:-手动生成}"
    cd "$BACKEND_DIR"
    source venv/bin/activate
    python -m app.tools.admin generate-code --type year --count "$COUNT" --remark "$REMARK"
    cd "$PROJECT_DIR"
}

cmd_code_list() {
    cd "$BACKEND_DIR"
    source venv/bin/activate
    python -m app.tools.admin list-codes
    cd "$PROJECT_DIR"
}

cmd_logs() {
    if [ -f /tmp/shushui_backend.log ]; then
        tail -50 /tmp/shushui_backend.log
    elif [ -f /tmp/shushui_backend_dev.log ]; then
        tail -50 /tmp/shushui_backend_dev.log
    else
        echo -e "${YELLOW}未找到日志文件，服务可能未运行${NC}"
    fi
}

cmd_rebuild_db() {
    echo -e "${YELLOW}🔄 重建知识库向量索引...${NC}"
    cd "$BACKEND_DIR"
    source venv/bin/activate
    python -c "
import requests
res = requests.post('http://localhost:8000/api/admin/knowledge/rebuild')
print(res.json())
"
    cd "$PROJECT_DIR"
}

cmd_shell() {
    echo -e "${CYAN}🐍 进入后端Python虚拟环境${NC}"
    echo -e "${YELLOW}输入 exit 退出${NC}"
    echo ""
    cd "$BACKEND_DIR"
    source venv/bin/activate
    exec $SHELL
}

# 主命令分发
case "${1:-help}" in
    start)    cmd_start ;;
    dev)      cmd_dev ;;
    public)   cmd_public ;;
    stop)     cmd_stop ;;
    status)   cmd_status ;;
    build)    cmd_build ;;
    rebuild)  cmd_rebuild ;;
    code:month) cmd_code_month "$@" ;;
    code:year)  cmd_code_year "$@" ;;
    code:list)  cmd_code_list ;;
    logs)     cmd_logs ;;
    rebuild-db) cmd_rebuild_db ;;
    shell)    cmd_shell ;;
    help|--help|-h|"") show_help ;;
    *)
        echo -e "${RED}❌ 未知命令: $1${NC}"
        show_help
        exit 1
        ;;
esac
