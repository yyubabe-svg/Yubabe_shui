from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from datetime import datetime
from app.core.database import Base


class PaymentOrder(Base):
    """支付订单"""
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    out_trade_no = Column(String(64), unique=True, index=True, nullable=False)  # 商户订单号
    user_name = Column(String(50), index=True, nullable=False)  # 付款用户姓名
    trade_no = Column(String(64), nullable=True)  # 支付宝交易号
    amount = Column(Integer, nullable=False)  # 金额（分）
    subject = Column(String(128), nullable=False)  # 订单标题
    body = Column(String(256), nullable=True)  # 订单描述
    plan_type = Column(String(20), nullable=False)  # month / year
    duration_days = Column(Integer, nullable=False)  # 开通天数
    status = Column(String(32), default="WAIT_BUYER_PAY", nullable=False)
    # WAIT_BUYER_PAY: 等待付款
    # TRADE_SUCCESS: 支付成功
    # TRADE_FINISHED: 交易完成
    # TRADE_CLOSED: 交易关闭
    qr_code = Column(String(512), nullable=True)  # 二维码链接
    paid_at = Column(DateTime, nullable=True)  # 支付时间
    activated = Column(Boolean, default=False)  # 是否已激活Pro
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    remark = Column(String(256), nullable=True)
