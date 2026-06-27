"""
支付相关API - 电脑网站支付（alipay.trade.page.pay）
流程：
1. 创建订单 -> 返回支付跳转URL
2. 用户访问/pay/{out_trade_no} -> 自动提交表单跳转支付宝收银台
3. 支付完成后支付宝跳转return_url（同步回调，展示结果）
4. 支付宝异步通知notify_url（异步回调，更新订单状态，激活Pro）
5. 前端轮询/order-status确认支付结果
"""
import uuid
import base64
import os
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user_usage import UserUsage
from app.models.payment import PaymentOrder
from app.services.alipay_service import alipay_service

router = APIRouter()


class CreateOrderRequest(BaseModel):
    plan_type: str = Field(..., description="month 或 year")
    user_name: Optional[str] = Field(None, description="用户名（可选，也可通过header传递）")


class CreateOrderResponse(BaseModel):
    out_trade_no: str
    pay_url: str  # 前端跳转到这个URL进行支付
    amount: float
    plan_type: str
    duration_days: int
    alipay_enabled: bool
    manual_payment: bool = False
    manual_qr_url: Optional[str] = None
    manual_qr_base64: Optional[str] = None  # base64编码的收款码图片，直接用于img src
    message: str = ""


class OrderStatusResponse(BaseModel):
    out_trade_no: str
    status: str
    paid: bool
    activated: bool
    amount: float
    trade_no: Optional[str] = None
    is_pro: bool = False
    pro_expire_at: Optional[str] = None


def _get_plan_info(plan_type: str) -> tuple:
    """获取套餐信息: (价格元, 天数, 标题)"""
    if plan_type == "month":
        return float(settings.PRICE_MONTHLY), 30, "蜀水智库AI Pro 月卡"
    elif plan_type == "year":
        return float(settings.PRICE_YEARLY), 365, "蜀水智库AI Pro 年卡"
    else:
        raise HTTPException(status_code=400, detail="不支持的套餐类型")


def _generate_out_trade_no() -> str:
    """生成商户订单号"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"SS{timestamp}{short_uuid}"


@router.post("/create-order", response_model=CreateOrderResponse, summary="创建支付订单")
async def create_order(
    req: CreateOrderRequest,
    request: Request,
    x_user_name: str = Header(None),
    x_username: str = Header(None),
    db: Session = Depends(get_db),
):
    """创建支付订单（用户不存在时自动创建）"""
    # 多种方式获取用户名：请求体 > X-User-Name header > X-Username header
    user_name = req.user_name or x_user_name or x_username
    # 打印调试信息
    print(f"[Payment] create-order called")
    print(f"[Payment] req.user_name='{req.user_name}', x_user_name='{x_user_name}', x_username='{x_username}'")
    print(f"[Payment] Final user_name='{user_name}'")
    
    if not user_name or not user_name.strip():
        raise HTTPException(status_code=401, detail="请先登录（输入姓名）后再进行支付")
    
    user_name = user_name.strip()

    user = db.query(UserUsage).filter(UserUsage.name == user_name).first()
    if not user:
        from datetime import datetime as dt
        user = UserUsage(
            name=user_name,
            pin_hash=None,
            is_pro=False,
            total_upload_bytes=0,
            daily_qa_count=0,
            daily_qa_date=dt.utcnow().strftime("%Y-%m-%d"),
            iso_used_count=0,
            pro_expire_at=None,
            created_at=dt.utcnow(),
            last_active_at=dt.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 检查是否有未支付的有效订单（2小时内）
    two_hours_ago = datetime.utcnow() - timedelta(hours=2)
    existing_order = (
        db.query(PaymentOrder)
        .filter(
            PaymentOrder.user_name == user_name,
            PaymentOrder.status.in_(["WAIT_BUYER_PAY", "PENDING_MANUAL"]),
            PaymentOrder.created_at > two_hours_ago,
        )
        .order_by(PaymentOrder.created_at.desc())
        .first()
    )

    amount_yuan, duration_days, subject = _get_plan_info(req.plan_type)
    amount_fen = int(amount_yuan * 100)

    manual_payment = False
    manual_qr_url = None
    message = ""
    order_status = "WAIT_BUYER_PAY"
    out_trade_no = existing_order.out_trade_no if existing_order else _generate_out_trade_no()

    if existing_order:
        if existing_order.status == "PENDING_MANUAL":
            manual_payment = True
            manual_qr_url = settings.MANUAL_PAYMENT_QR_URL
            message = settings.MANUAL_PAYMENT_NOTE
        else:
            message = "已有待支付订单"
    else:
        body = f"蜀水智库AI Pro {('月卡' if req.plan_type == 'month' else '年卡')} - {user.name}"

        # 优先使用支付宝电脑网站支付
        if alipay_service.enabled:
            print(f"[Payment] Alipay enabled, creating page pay order")
            message = "正在跳转到支付宝收银台..."
            # 预构建表单验证签名是否正常
            success, msg, _ = alipay_service.build_page_pay_form(
                out_trade_no=out_trade_no,
                total_amount=amount_yuan,
                subject=subject,
                body=body,
            )
            if not success:
                print(f"[Payment] Alipay build form failed: {msg}, falling back to manual")
                if settings.MANUAL_PAYMENT_ENABLED:
                    manual_payment = True
                    manual_qr_url = settings.MANUAL_PAYMENT_QR_URL
                    order_status = "PENDING_MANUAL"
                    message = f"在线支付暂不可用（{msg}）。{settings.MANUAL_PAYMENT_NOTE}"
                else:
                    raise HTTPException(status_code=500, detail=msg)
        elif settings.MANUAL_PAYMENT_ENABLED:
            # 支付宝未配置，使用个人收款码模式
            manual_payment = True
            manual_qr_url = settings.MANUAL_PAYMENT_QR_URL
            order_status = "PENDING_MANUAL"
            message = settings.MANUAL_PAYMENT_NOTE
        else:
            raise HTTPException(status_code=503, detail="支付未配置，请联系管理员")

        # 保存订单
        order = PaymentOrder(
            out_trade_no=out_trade_no,
            user_name=user.name,
            amount=amount_fen,
            subject=subject,
            body=body,
            plan_type=req.plan_type,
            duration_days=duration_days,
            status=order_status,
            qr_code=None,
        )
        db.add(order)
        db.commit()

    pay_url = f"/api/payment/pay/{out_trade_no}"

    # 读取收款码图片并转为base64（个人收款码模式）
    manual_qr_base64 = None
    if manual_payment and manual_qr_url:
        try:
            # backend目录上一层就是项目根目录 shushui-ai
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            project_root = os.path.dirname(backend_dir)  # shushui-ai
            # 尝试多个可能的路径
            possible_paths = [
                os.path.join(project_root, "frontend", "public", manual_qr_url.lstrip("/")),
                os.path.join(project_root, "frontend", "dist", manual_qr_url.lstrip("/")),
                # 也尝试工作目录
                os.path.join(os.getcwd(), "..", "frontend", "public", manual_qr_url.lstrip("/")),
                os.path.join(os.getcwd(), "frontend", "public", manual_qr_url.lstrip("/")),
            ]
            print(f"[Payment] Looking for QR code, backend_dir={backend_dir}, project_root={project_root}")
            for qr_path in possible_paths:
                qr_path_norm = os.path.normpath(qr_path)
                print(f"[Payment] Trying: {qr_path_norm}, exists: {os.path.isfile(qr_path_norm)}")
                if os.path.isfile(qr_path_norm):
                    with open(qr_path_norm, "rb") as f:
                        qr_data = f.read()
                    # 根据文件头（magic number）判断真实图片类型
                    mime_type = "image/png"  # 默认
                    if qr_data[:2] == b'\xff\xd8':
                        mime_type = "image/jpeg"
                    elif qr_data[:8] == b'\x89PNG\r\n\x1a\n':
                        mime_type = "image/png"
                    elif qr_data[:6] in (b'GIF87a', b'GIF89a'):
                        mime_type = "image/gif"
                    elif qr_data[:4] == b'RIFF' and qr_data[8:12] == b'WEBP':
                        mime_type = "image/webp"
                    manual_qr_base64 = f"data:{mime_type};base64," + base64.b64encode(qr_data).decode("utf-8")
                    print(f"[Payment] QR code loaded! mime={mime_type}, size: {len(qr_data)} bytes")
                    break
        except Exception as e:
            print(f"[Payment] Failed to load QR code: {e}")
            import traceback
            traceback.print_exc()

    return CreateOrderResponse(
        out_trade_no=out_trade_no,
        pay_url=pay_url,
        amount=amount_yuan,
        plan_type=req.plan_type,
        duration_days=duration_days,
        alipay_enabled=alipay_service.enabled,
        manual_payment=manual_payment,
        manual_qr_url=manual_qr_url,
        manual_qr_base64=manual_qr_base64,
        message=message,
    )


@router.get("/pay/{out_trade_no}", summary="支付宝支付跳转页面")
async def pay_page(
    out_trade_no: str,
    db: Session = Depends(get_db),
):
    """返回自动提交的支付宝支付表单页面"""
    order = db.query(PaymentOrder).filter(PaymentOrder.out_trade_no == out_trade_no).first()
    if not order:
        return HTMLResponse(content="<h1>订单不存在</h1>", status_code=404)
    
    if order.status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return RedirectResponse(url="/?paid=1")
    
    if order.status == "PENDING_MANUAL":
        return RedirectResponse(url="/?manual=1")

    if not alipay_service.enabled:
        return HTMLResponse(content="<h1>支付宝支付未配置</h1>", status_code=503)

    success, msg, form_html = alipay_service.build_page_pay_form(
        out_trade_no=order.out_trade_no,
        total_amount=order.amount / 100,
        subject=order.subject,
        body=order.body,
    )

    if not success:
        return HTMLResponse(content=f"<h1>支付发起失败</h1><p>{msg}</p>", status_code=500)

    return HTMLResponse(content=form_html)


@router.get("/return", summary="支付宝同步跳转回调（支付完成后跳转）")
async def alipay_return(
    request: Request,
    db: Session = Depends(get_db),
):
    """支付宝支付完成后同步跳转页面（仅用于展示，最终结果以异步通知/查询为准）"""
    params = dict(request.query_params)
    out_trade_no = params.get("out_trade_no")
    
    # 构建结果页面
    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>支付结果</title>
<style>
body{font-family:sans-serif;text-align:center;padding:80px 20px;max-width:500px;margin:0 auto;}
.success{color:#00b578;}
h1{font-size:24px;margin-bottom:16px;}
p{color:#666;margin-bottom:24px;}
.btn{display:inline-block;padding:12px 32px;background:#1677ff;color:#fff;text-decoration:none;border-radius:8px;}
</style>
</head>
<body>
"""
    
    if out_trade_no:
        # 主动查询订单状态
        order = db.query(PaymentOrder).filter(PaymentOrder.out_trade_no == out_trade_no).first()
        paid = False
        if order:
            if alipay_service.enabled and order.status == "WAIT_BUYER_PAY":
                success, trade_status, trade_no = await alipay_service.query_trade(out_trade_no)
                if success and trade_status == "TRADE_SUCCESS":
                    alipay_service.activate_pro_for_order(db, order)
                    db.refresh(order)
                    paid = True
            paid = paid or order.activated
        
        if paid:
            html += """
<div class="success">
<h1>✅ 支付成功</h1>
<p>Pro专业版已激活，感谢您的支持！</p>
</div>
"""
        else:
            html += """
<h1>⏳ 支付处理中</h1>
<p>支付结果确认中，请稍候返回查看。如已付款，系统将自动为您开通Pro。</p>
"""
    else:
        html += """
<h1>支付完成</h1>
<p>正在返回首页...</p>
"""
    
    html += """
<a href="/" class="btn">返回首页</a>
<script>setTimeout(function(){window.location.href='/'}, 3000);</script>
</body>
</html>"""
    
    return HTMLResponse(content=html)


@router.post("/alipay/notify", summary="支付宝异步通知")
async def alipay_notify(
    request: Request,
    db: Session = Depends(get_db),
):
    """接收支付宝异步支付通知（重要：此接口用于更新订单状态、激活Pro）"""
    form_data = await request.form()
    params = dict(form_data)
    print(f"[Payment] Received Alipay notify: out_trade_no={params.get('out_trade_no')}, trade_status={params.get('trade_status')}")

    # 验签
    if alipay_service.enabled and not alipay_service._verify_sign(dict(params)):
        print(f"[Payment] Sign verify FAILED")
        return PlainTextResponse("fail")

    out_trade_no = params.get("out_trade_no")
    trade_status = params.get("trade_status")
    trade_no = params.get("trade_no")

    if not out_trade_no:
        return PlainTextResponse("fail")

    order = db.query(PaymentOrder).filter(PaymentOrder.out_trade_no == out_trade_no).first()
    if not order:
        return PlainTextResponse("fail")

    # 处理支付成功
    if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        if order.status != "TRADE_SUCCESS" and not order.activated:
            order.trade_no = trade_no
            alipay_service.activate_pro_for_order(db, order)
            print(f"[Payment] Order {out_trade_no} paid successfully, Pro activated for {order.user_name}")

    elif trade_status == "TRADE_CLOSED":
        order.status = "TRADE_CLOSED"
        db.commit()

    return PlainTextResponse("success")


@router.get("/order-status/{out_trade_no}", response_model=OrderStatusResponse, summary="查询订单状态")
async def order_status(
    out_trade_no: str,
    x_user_name: str = Header(None),
    db: Session = Depends(get_db),
):
    """查询订单支付状态（前端轮询用）"""
    order = db.query(PaymentOrder).filter(PaymentOrder.out_trade_no == out_trade_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 如果订单仍在等待支付且支付宝已启用，主动查询支付宝
    if order.status == "WAIT_BUYER_PAY" and alipay_service.enabled:
        success, trade_status, trade_no = await alipay_service.query_trade(out_trade_no)
        if success and trade_status == "TRADE_SUCCESS":
            order.trade_no = trade_no
            alipay_service.activate_pro_for_order(db, order)
            db.refresh(order)
        elif success and trade_status == "TRADE_CLOSED":
            order.status = "TRADE_CLOSED"
            db.commit()

    user = db.query(UserUsage).filter(UserUsage.name == order.user_name).first()

    return OrderStatusResponse(
        out_trade_no=order.out_trade_no,
        status=order.status,
        paid=order.status in ("TRADE_SUCCESS", "TRADE_FINISHED"),
        activated=order.activated,
        amount=order.amount / 100,
        trade_no=order.trade_no,
        is_pro=user.is_pro_active() if user else False,
        pro_expire_at=user.pro_expire_at.strftime("%Y-%m-%d") if user and user.pro_expire_at else None,
    )


@router.get("/plans", summary="获取套餐定价")
async def get_plans():
    """获取套餐信息"""
    return {
        "monthly": {
            "price": settings.PRICE_MONTHLY,
            "days": 30,
            "name": "Pro 月卡",
        },
        "yearly": {
            "price": settings.PRICE_YEARLY,
            "days": 365,
            "name": "Pro 年卡",
            "savings": f"省{settings.PRICE_MONTHLY * 12 - settings.PRICE_YEARLY}元",
        },
        "alipay_enabled": alipay_service.enabled,
        "manual_payment_enabled": settings.MANUAL_PAYMENT_ENABLED,
        "manual_payment_qr_url": settings.MANUAL_PAYMENT_QR_URL,
        "manual_payment_note": settings.MANUAL_PAYMENT_NOTE,
        "admin_wechat": settings.ADMIN_WECHAT,
    }
