#!/bin/bash
# 管理员手动激活用户Pro脚本
# 使用方法: ./activate-user.sh <用户名> [天数]
# 示例: ./activate-user.sh 张三 365

cd "$(dirname "$0")/backend"
source venv/bin/activate

USER_NAME="$1"
DAYS="${2:-365}"
ADMIN_TOKEN="shushui-admin-change-me"
BASE_URL="http://localhost:8000"

if [ -z "$USER_NAME" ]; then
    echo "使用方法: $0 <用户名> [激活天数，默认365天]"
    echo ""
    echo "示例:"
    echo "  $0 张三          # 激活年卡（365天）"
    echo "  $0 李四 30       # 激活月卡（30天）"
    echo ""
    echo ""
    echo "=== 用户列表 ==="
    curl -s "$BASE_URL/api/admin/users" -H "X-Admin-Token: $ADMIN_TOKEN" | python3 -m json.tool
    exit 1
fi

echo "正在为用户 $USER_NAME 激活 $DAYS 天Pro..."
echo ""

curl -s -X POST "$BASE_URL/api/admin/activate-user" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -d "{\"user_name\": \"$USER_NAME\", \"days\": $DAYS}" | python3 -m json.tool

echo ""
echo "完成！"
