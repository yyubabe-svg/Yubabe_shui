#!/usr/bin/env python3
"""
支付宝支付配置辅助工具
用法:
  python setup_alipay.py          # 交互式配置
  python setup_alipay.py key      # 仅生成密钥并显示公钥
  python setup_alipay.py status   # 查看当前配置状态
"""
import os
import sys
import re
from pathlib import Path

KEYS_DIR = Path(__file__).parent / "keys"
ENV_FILE = Path(__file__).parent / ".env"


def read_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def write_env_value(key: str, value: str):
    """更新.env中的单个配置项"""
    content = read_file(ENV_FILE)
    if not content:
        content = "# 蜀水智库 AI 环境变量配置\n"
    
    # 处理引号
    if value and not value.startswith('"') and (' ' in value or '\n' in value):
        value = f'"{value}"'
    
    pattern = rf'^{key}=.*$'
    new_line = f'{key}={value}'
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content += f'\n{new_line}\n'
    
    ENV_FILE.write_text(content, encoding="utf-8")


def generate_keys():
    """生成RSA密钥对"""
    KEYS_DIR.mkdir(exist_ok=True)
    private_key_path = KEYS_DIR / "app_private_key.pem"
    public_key_path = KEYS_DIR / "app_public_key.pem"
    
    if private_key_path.exists() and public_key_path.exists():
        print("⚠️  应用密钥已存在，跳过生成")
        return public_key_path
    
    print("🔑 正在生成RSA2密钥对...")
    os.system(f'openssl genrsa -out "{private_key_path}" 2048 2>/dev/null')
    os.system(f'openssl rsa -in "{private_key_path}" -pubout -out "{public_key_path}" 2>/dev/null')
    print(f"✅ 应用私钥: {private_key_path}")
    print(f"✅ 应用公钥: {public_key_path}")
    print()
    return public_key_path


def show_public_key():
    """显示应用公钥（用于粘贴到支付宝开放平台）"""
    public_key_path = KEYS_DIR / "app_public_key.pem"
    public_key = read_file(public_key_path)
    if not public_key:
        print("❌ 公钥不存在，请先运行: python setup_alipay.py key")
        return None
    
    # 提取密钥内容（去掉头尾标记和换行）
    key_content = public_key
    key_content = re.sub(r'-----BEGIN PUBLIC KEY-----', '', key_content)
    key_content = re.sub(r'-----END PUBLIC KEY-----', '', key_content)
    key_content = key_content.replace('\n', '').strip()
    
    print("=" * 60)
    print("📋 应用公钥（复制以下内容粘贴到支付宝开放平台）：")
    print("=" * 60)
    print(key_content)
    print("=" * 60)
    print()
    return key_content


def save_alipay_public_key(key_content: str) -> Path:
    """保存支付宝公钥到文件"""
    alipay_key_path = KEYS_DIR / "alipay_public_key.pem"
    
    # 如果用户粘贴的是纯内容（不含PEM头尾），自动添加
    key_content = key_content.strip()
    if '-----BEGIN PUBLIC KEY-----' not in key_content:
        key_content = f"-----BEGIN PUBLIC KEY-----\n{key_content}\n-----END PUBLIC KEY-----"
    
    alipay_key_path.write_text(key_content, encoding="utf-8")
    print(f"✅ 支付宝公钥已保存到: {alipay_key_path}")
    return alipay_key_path


def interactive_setup():
    """交互式配置"""
    print()
    print("=" * 60)
    print("  蜀水智库 AI - 支付宝支付配置工具")
    print("=" * 60)
    print()
    
    # 1. 生成密钥
    generate_keys()
    show_public_key()
    
    print("📝 操作步骤：")
    print()
    print("【推荐：先用沙箱环境测试】")
    print("  1. 浏览器打开支付宝沙箱环境：")
    print("     https://open.alipay.com/develop/sandbox/app")
    print("  2. 登录你的支付宝账号（个人账号即可）")
    print("  3. 在沙箱页面找到 APP_ID，复制填入下方")
    print("  4. 点击'开发信息' → '接口加签方式' → '设置'")
    print("  5. 选择'公钥模式'，将上面的应用公钥粘贴进去")
    print("  6. 保存后，平台会显示'支付宝公钥'，复制填入下方")
    print("  7. 下载'支付宝沙箱版'APP用于扫码测试")
    print("  8. 沙箱买家账号在沙箱页面可查看（有测试余额）")
    print()
    print("【正式环境】需要企业/个体工商户资质：")
    print("  1. 在支付宝开放平台创建应用并签约'订单码支付'")
    print("  2. 同样方式配置应用公钥并获取支付宝公钥")
    print()
    print("-" * 60)
    print()
    
    # 获取AppId
    app_id = input("请输入支付宝 APP_ID（沙箱应用ID）: ").strip()
    if not app_id:
        print("❌ APP_ID不能为空")
        return
    
    # 获取支付宝公钥
    print()
    alipay_public_key = input("请输入支付宝公钥（粘贴平台提供的公钥）: ").strip()
    if not alipay_public_key:
        print("❌ 支付宝公钥不能为空")
        return
    save_alipay_public_key(alipay_public_key)
    
    # 环境选择
    is_sandbox = input("\n是否使用沙箱环境？(Y/n): ").strip().lower() != 'n'
    
    # 公网地址
    public_url = input("\n请输入服务器公网地址（本地测试直接回车）: ").strip()
    if not public_url:
        public_url = "http://localhost:8000"
        print(f"  使用本地地址: {public_url}")
        print("  ⚠️  本地地址无法接收支付宝异步通知，但前端轮询查询可正常工作")
        print("  💡 如需接收异步通知，可使用内网穿透工具（如ngrok、cpolar）")
    
    # 管理员微信
    admin_wechat = input("\n请输入管理员微信号（可选，显示在升级弹窗中）: ").strip()
    
    # 写入配置
    write_env_value("ALIPAY_ENABLED", "true")
    write_env_value("ALIPAY_APP_ID", app_id)
    write_env_value("ALIPAY_SANDBOX", "true" if is_sandbox else "false")
    write_env_value("ALIPAY_NOTIFY_URL", f"{public_url}/api/payment/alipay/notify")
    write_env_value("SERVER_PUBLIC_URL", public_url)
    if admin_wechat:
        write_env_value("ADMIN_WECHAT", admin_wechat)
    
    print()
    print("🎉 支付宝配置完成！")
    print()
    print("下一步：")
    print("  1. 重启后端服务: cd backend && source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("  2. 访问 http://localhost:8000")
    print("  3. 输入姓名登录 → 点击右上角用户头像 → 升级Pro")
    print("  4. 选择套餐 → 支付宝扫码支付 → 用沙箱APP扫码")
    print()
    if is_sandbox:
        print("📌 沙箱测试提醒：")
        print("  - 必须使用'支付宝沙箱版'APP扫码，正式支付宝APP无法识别沙箱二维码")
        print("  - 使用沙箱买家账号登录沙箱APP（在沙箱页面查看账号和密码）")
        print("  - 沙箱环境不会产生真实扣款")
        print()


def show_status():
    """显示当前配置状态"""
    print()
    print("=" * 60)
    print("  支付宝配置状态")
    print("=" * 60)
    print()
    
    env_content = read_file(ENV_FILE)
    
    def get_env(key, default="未配置"):
        match = re.search(rf'^{key}=(.*)$', env_content, re.MULTILINE)
        if match:
            val = match.group(1).strip('"\'')
            return val if val else default
        return default
    
    enabled = get_env("ALIPAY_ENABLED", "false").lower() == "true"
    print(f"  支付功能: {'已启用 ✓' if enabled else '未启用（激活码模式）'}")
    print(f"  APP_ID:   {get_env('ALIPAY_APP_ID')}")
    print(f"  沙箱模式: {'是' if get_env('ALIPAY_SANDBOX', 'true').lower() == 'true' else '否'}")
    print(f"  公网地址: {get_env('SERVER_PUBLIC_URL')}")
    print(f"  管理员微信: {get_env('ADMIN_WECHAT', '未设置')}")
    print()
    
    print("  密钥文件状态：")
    files = [
        ("app_private_key.pem (应用私钥)", KEYS_DIR / "app_private_key.pem"),
        ("app_public_key.pem  (应用公钥)", KEYS_DIR / "app_public_key.pem"),
        ("alipay_public_key.pem (支付宝公钥)", KEYS_DIR / "alipay_public_key.pem"),
    ]
    for name, path in files:
        exists = path.exists() and path.stat().st_size > 0
        print(f"    {name}: {'存在 ✓' if exists else '不存在 ✗'}")
    print()
    
    if enabled:
        print("  如需禁用支付宝，编辑 .env 设置 ALIPAY_ENABLED=false")
    else:
        print("  运行 python setup_alipay.py 开始配置")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            show_status()
        elif cmd == "key":
            generate_keys()
            show_public_key()
        elif cmd == "disable":
            write_env_value("ALIPAY_ENABLED", "false")
            print("✅ 支付宝支付已禁用（将使用激活码模式）")
        else:
            print(__doc__)
    else:
        interactive_setup()
