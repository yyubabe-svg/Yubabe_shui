#!/bin/bash
# ============================================
# 蜀水智库AI - 火山引擎一键部署脚本
# 使用方法：chmod +x deploy.sh && ./deploy.sh
# ============================================

set -e

echo "========================================"
echo "  蜀水智库AI - 火山引擎生产部署"
echo "========================================"
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  建议使用root用户运行，或在命令前加 sudo"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. 安装Docker和Docker Compose
echo ""
echo "[1/5] 检查Docker环境..."
if ! command -v docker &> /dev/null; then
    echo "📦 正在安装Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker安装完成"
else
    echo "✅ Docker已安装: $(docker --version)"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "📦 正在安装Docker Compose..."
    apt-get update && apt-get install -y docker-compose-plugin
    echo "✅ Docker Compose安装完成"
else
    echo "✅ Docker Compose已安装"
fi

# 2. 创建必要目录
echo ""
echo "[2/5] 创建数据目录..."
mkdir -p backend/uploads backend/vector_db backend/db_data backend/resources/iso_templates backend/keys
# 确保数据库文件存在（避免Docker将挂载点创建为目录）
if [ ! -f backend/db_data/shushui_ai.db ]; then
    touch backend/db_data/shushui_ai.db
fi
echo "✅ 数据目录已创建"

# 3. 检查.env.prod配置
echo ""
echo "[3/5] 检查环境配置..."
if [ ! -f .env.prod ]; then
    echo "❌ 未找到 .env.prod 配置文件"
    exit 1
fi

# 提示用户修改配置
if grep -q "YOUR_SERVER_IP" .env.prod; then
    echo "⚠️  检测到 .env.prod 中 YOUR_SERVER_IP 未替换"
    echo "   请先编辑 .env.prod 文件，将 YOUR_SERVER_IP 替换为你的服务器公网IP或域名"
    echo ""
    read -p "是否现在编辑配置？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        nano .env.prod || vi .env.prod
    else
        echo "   请部署前手动修改: nano .env.prod"
    fi
fi

# 4. 构建并启动服务
echo ""
echo "[4/5] 构建并启动服务（首次构建需要5-10分钟）..."
echo ""

# 检测docker compose命令
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

$COMPOSE_CMD down --remove-orphans 2>/dev/null || true
$COMPOSE_CMD up -d --build

# 5. 等待服务启动并检查
echo ""
echo "[5/5] 等待服务启动..."
sleep 10

echo ""
echo "========================================"
echo "  🎉 部署完成！"
echo "========================================"
echo ""

# 获取公网IP
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_IP")

echo "📋 服务状态："
$COMPOSE_CMD ps
echo ""
echo "🌐 访问地址："
echo "   首页:  http://$PUBLIC_IP"
echo "   API文档: http://$PUBLIC_IP/docs"
echo ""
echo "📝 常用命令："
echo "   查看日志: $COMPOSE_CMD logs -f"
echo "   查看后端日志: $COMPOSE_CMD logs -f backend"
echo "   重启服务: $COMPOSE_CMD restart"
echo "   停止服务: $COMPOSE_CMD down"
echo "   更新部署: git pull && $COMPOSE_CMD up -d --build"
echo ""
echo "⚠️  重要提示："
echo "   1. 请确保云服务器安全组已开放 80 端口"
echo "   2. 请修改 .env.prod 中的 SECRET_KEY 和 ADMIN_TOKEN"
echo "   3. 如需HTTPS，请配置域名和SSL证书"
echo ""
