"""
蜀水智库 AI - 管理员命令行工具

用法：
    cd backend
    python -m app.tools.admin generate-code --type month --count 5 --remark "6月推广"
    python -m app.tools.admin generate-code --type year --count 1 --remark "李四年费"
    python -m app.tools.admin list-users
    python -m app.tools.admin grant-pro --name "张三" --days 30 --remark "免费赠送"
    python -m app.tools.admin revoke-pro --name "张三"
    python -m app.tools.admin stats
"""
import sys
import os
import argparse
import secrets
import string
from datetime import datetime, timedelta

# 确保backend目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.user_usage import UserUsage, ActivationCode
from app.models.qa_log import QALog
from app.models.document import Document


def generate_code_string(length=16):
    """生成易读的激活码，排除易混淆字符"""
    alphabet = string.ascii_uppercase.replace('O', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def format_code(code_str):
    """格式化激活码为 XXXX-XXXX-XXXX-XXXX"""
    return '-'.join([code_str[i:i+4] for i in range(0, len(code_str), 4)])


def format_bytes(bytes_val):
    """格式化字节数"""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val / 1024 / 1024:.1f} MB"


def cmd_generate_code(args):
    """生成激活码"""
    db = SessionLocal()
    try:
        if args.type == 'month':
            duration_days = 30
            type_label = '月卡(30天)'
        elif args.type == 'year':
            duration_days = 365
            type_label = '年卡(365天)'
        else:
            print(f"错误：不支持的类型 '{args.type}'，请使用 month 或 year")
            return

        codes = []
        for i in range(args.count):
            # 生成不重复的激活码
            while True:
                raw = generate_code_string(16)
                exists = db.query(ActivationCode).filter(ActivationCode.code == raw).first()
                if not exists:
                    break

            code = ActivationCode(
                code=raw,
                code_type=args.type,
                duration_days=duration_days,
                is_used=False,
                remark=args.remark,
            )
            db.add(code)
            codes.append(raw)

        db.commit()

        print(f"\n✅ 成功生成 {args.count} 个{type_label}激活码：")
        print("-" * 60)
        for raw in codes:
            print(f"  {format_code(raw)}")
        print("-" * 60)
        if args.remark:
            print(f"备注：{args.remark}")
        print()
    finally:
        db.close()


def cmd_list_users(args):
    """列出所有用户"""
    db = SessionLocal()
    try:
        users = db.query(UserUsage).order_by(UserUsage.created_at.desc()).all()
        
        if not users:
            print("暂无用户")
            return

        print(f"\n共 {len(users)} 个用户：")
        print("-" * 90)
        print(f"{'姓名':<12} {'Pro':<6} {'到期时间':<20} {'存储使用':<12} {'今日问答':<10} {'ISO使用':<8} {'最后活跃'}")
        print("-" * 90)
        
        for u in users:
            is_pro = "✓" if u.is_pro_active() else "✗"
            expire = u.pro_expire_at.strftime('%Y-%m-%d') if u.pro_expire_at else "-"
            storage = format_bytes(u.total_upload_bytes)
            qa = str(u.daily_qa_count)
            iso = str(u.iso_used_count)
            last_active = u.last_active_at.strftime('%Y-%m-%d %H:%M') if u.last_active_at else "-"
            print(f"{u.name:<12} {is_pro:<6} {expire:<20} {storage:<12} {qa:<10} {iso:<8} {last_active}")
        
        print("-" * 90)
        print()
    finally:
        db.close()


def cmd_grant_pro(args):
    """直接给用户开通Pro"""
    db = SessionLocal()
    try:
        user = db.query(UserUsage).filter(UserUsage.name == args.name).first()
        if not user:
            # 如果用户不存在，创建一个
            user = UserUsage(
                name=args.name,
                is_pro=True,
                pro_expire_at=datetime.utcnow() + timedelta(days=args.days),
                total_upload_bytes=0,
                daily_qa_count=0,
                daily_qa_date=datetime.utcnow().strftime("%Y-%m-%d"),
                iso_used_count=0,
            )
            db.add(user)
            action = "创建新用户并开通Pro"
        else:
            # 续期
            base = user.pro_expire_at if user.is_pro_active() else datetime.utcnow()
            user.is_pro = True
            user.pro_expire_at = base + timedelta(days=args.days)
            action = f"为用户续期Pro {args.days} 天"

        db.commit()
        expire_str = user.pro_expire_at.strftime('%Y-%m-%d %H:%M')
        print(f"\n✅ {action}成功")
        print(f"  用户：{args.name}")
        print(f"  到期：{expire_str}")
        if args.remark:
            print(f"  备注：{args.remark}")
        print()
    finally:
        db.close()


def cmd_revoke_pro(args):
    """取消用户Pro"""
    db = SessionLocal()
    try:
        user = db.query(UserUsage).filter(UserUsage.name == args.name).first()
        if not user:
            print(f"错误：用户 '{args.name}' 不存在")
            return

        user.is_pro = False
        user.pro_expire_at = None
        db.commit()

        print(f"\n✅ 已取消用户 '{args.name}' 的Pro权限\n")
    finally:
        db.close()


def cmd_list_codes(args):
    """列出激活码"""
    db = SessionLocal()
    try:
        codes = db.query(ActivationCode).order_by(ActivationCode.created_at.desc()).all()
        
        if not codes:
            print("暂无激活码")
            return

        unused = [c for c in codes if not c.is_used]
        used = [c for c in codes if c.is_used]
        
        print(f"\n共 {len(codes)} 个激活码（未使用: {len(unused)}，已使用: {len(used)}）")
        print("-" * 100)
        print(f"{'激活码':<24} {'类型':<8} {'天数':<6} {'状态':<8} {'使用者':<12} {'创建时间':<20} {'备注'}")
        print("-" * 100)
        
        for c in codes:
            code_type = '月卡' if c.code_type == 'month' else '年卡'
            status = '✓ 已用' if c.is_used else '○ 未用'
            used_by = c.used_by_name or '-'
            created = c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else '-'
            remark = c.remark or '-'
            print(f"{format_code(c.code):<24} {code_type:<8} {c.duration_days:<6} {status:<8} {used_by:<12} {created:<20} {remark}")
        
        print("-" * 100)
        print()
    finally:
        db.close()


def cmd_stats(args):
    """查看使用统计"""
    db = SessionLocal()
    try:
        total_users = db.query(UserUsage).count()
        pro_users = db.query(UserUsage).filter(UserUsage.is_pro == True).count()
        total_docs = db.query(Document).count()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        qa_today = db.query(QALog).filter(QALog.created_at >= datetime.utcnow() - timedelta(days=1)).count()
        
        # 计算总存储
        total_storage = db.query(UserUsage).all()
        total_bytes = sum(u.total_upload_bytes for u in total_storage)
        
        # 今日活跃
        active_today = db.query(UserUsage).filter(
            UserUsage.last_active_at >= datetime.utcnow() - timedelta(days=1)
        ).count()

        print(f"\n📊 蜀水智库 AI 使用统计")
        print("-" * 40)
        print(f"  总用户数：    {total_users}")
        print(f"  Pro用户数：   {pro_users}")
        print(f"  今日活跃：    {active_today}")
        print(f"  今日问答：    {qa_today}")
        print(f"  文档总数：    {total_docs}")
        print(f"  总存储使用：  {format_bytes(total_bytes)}")
        print("-" * 40)
        print()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='蜀水智库 AI 管理员工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # generate-code
    p_gen = subparsers.add_parser('generate-code', help='生成激活码')
    p_gen.add_argument('--type', required=True, choices=['month', 'year'], help='类型：month(月卡) / year(年卡)')
    p_gen.add_argument('--count', type=int, default=1, help='生成数量（默认1）')
    p_gen.add_argument('--remark', default='', help='备注（如"张三微信支付29元"）')

    # list-users
    subparsers.add_parser('list-users', help='列出所有用户')
    
    # list-codes
    subparsers.add_parser('list-codes', help='列出所有激活码')

    # grant-pro
    p_grant = subparsers.add_parser('grant-pro', help='直接给用户开通Pro')
    p_grant.add_argument('--name', required=True, help='用户姓名')
    p_grant.add_argument('--days', type=int, default=30, help='Pro天数（默认30）')
    p_grant.add_argument('--remark', default='', help='备注')

    # revoke-pro
    p_revoke = subparsers.add_parser('revoke-pro', help='取消用户Pro')
    p_revoke.add_argument('--name', required=True, help='用户姓名')

    # stats
    subparsers.add_parser('stats', help='查看使用统计')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'generate-code': cmd_generate_code,
        'list-users': cmd_list_users,
        'list-codes': cmd_list_codes,
        'grant-pro': cmd_grant_pro,
        'revoke-pro': cmd_revoke_pro,
        'stats': cmd_stats,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
