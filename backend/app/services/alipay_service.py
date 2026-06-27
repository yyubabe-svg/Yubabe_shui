"""
支付宝支付服务
使用订单码支付（precreate）+ 轮询查询模式
"""
import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.payment import PaymentOrder
from app.models.user_usage import UserUsage


def _generate_out_trade_no() -> str:
    """生成商户订单号：SS + 时间戳 + UUID前8位"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"SS{timestamp}{short_uuid}"


def _format_amount(yuan: float) -> str:
    """将元转为分的字符串（保留2位小数）"""
    return f"{yuan:.2f}"


def _html_escape(text: str) -> str:
    """HTML转义"""
    import html
    return html.escape(text, quote=True)


class AlipayService:
    """支付宝支付服务"""

    def __init__(self):
        self.app_id = settings.ALIPAY_APP_ID
        self.private_key = settings.get_alipay_private_key()
        self.alipay_public_key = settings.get_alipay_public_key()
        self.enabled = settings.ALIPAY_ENABLED and bool(self.app_id) and bool(self.private_key) and bool(self.alipay_public_key)
        self.sandbox = settings.ALIPAY_SANDBOX
        self.gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do" if self.sandbox else "https://openapi.alipay.com/gateway.do"
        self.charset = "UTF-8"
        self.sign_type = "RSA2"
        self.version = "1.0"

    def _sort_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """按键名字母排序，过滤空值和sign字段"""
        return {k: v for k, v in sorted(params.items()) if v is not None and v != "" and k != "sign"}

    def _sign(self, params: Dict[str, Any]) -> str:
        """RSA2签名"""
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            import base64

            # 构建待签名字符串
            sorted_params = self._sort_params(params)
            sign_content = "&".join(f"{k}={v}" for k, v in sorted_params.items())

            # 加载私钥
            private_key = serialization.load_pem_private_key(
                self.private_key.encode() if isinstance(self.private_key, str) else self.private_key,
                password=None,
                backend=default_backend()
            )

            # 签名
            signature = private_key.sign(
                sign_content.encode(self.charset),
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            return base64.b64encode(signature).decode(self.charset)
        except ImportError:
            # 如果cryptography未安装，尝试使用备选方案
            raise RuntimeError("请安装cryptography库: pip install cryptography")

    def _verify_sign(self, params: Dict[str, Any]) -> bool:
        """验签（验证支付宝异步通知）"""
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            import base64

            sign = params.pop("sign", None)
            sign_type = params.pop("sign_type", self.sign_type)
            if not sign:
                return False

            sorted_params = self._sort_params(params)
            sign_content = "&".join(f"{k}={v}" for k, v in sorted_params.items())

            # 加载支付宝公钥
            public_key = serialization.load_pem_public_key(
                self.alipay_public_key.encode() if isinstance(self.alipay_public_key, str) else self.alipay_public_key,
                backend=default_backend()
            )

            try:
                public_key.verify(
                    base64.b64decode(sign),
                    sign_content.encode(self.charset),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                return True
            except Exception:
                return False
        except ImportError:
            return False

    async def _request(self, method: str, biz_content: Dict[str, Any], notify_url: str = None, return_url: str = None) -> Dict[str, Any]:
        """发送请求到支付宝"""
        params = {
            "app_id": self.app_id,
            "method": method,
            "charset": self.charset,
            "sign_type": self.sign_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": self.version,
            "biz_content": json.dumps(biz_content, separators=(',', ':'), ensure_ascii=False),
        }
        if notify_url:
            params["notify_url"] = notify_url

        params["sign"] = self._sign(params)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.gateway, data=params)
            # 支付宝可能返回GBK编码，需要兼容处理
            try:
                result = response.json()
            except Exception:
                # 尝试用GBK解码
                try:
                    text = response.content.decode("gbk")
                    import json as _json
                    result = _json.loads(text)
                except Exception:
                    # 返回原始响应用于调试
                    return {"code": "-1", "msg": f"响应解析失败: {response.text[:200]}", "sub_msg": str(response.content[:200])}

        # 解析响应
        response_key = method.replace(".", "_") + "_response"
        if response_key in result:
            return result[response_key]
        return result

    async def precreate(
        self,
        out_trade_no: str,
        total_amount: float,
        subject: str,
        body: str = "",
        user_name: str = "",
    ) -> Tuple[bool, str, Optional[str]]:
        """
        预创建订单（生成支付二维码）
        返回: (success, message, qr_code)
        """
        if not self.enabled:
            return False, "支付宝支付未配置，请使用激活码方式开通Pro", None

        notify_url = settings.ALIPAY_NOTIFY_URL or f"{settings.SERVER_PUBLIC_URL}/api/payment/alipay/notify"

        biz_content = {
            "out_trade_no": out_trade_no,
            "total_amount": _format_amount(total_amount),
            "subject": subject,
            "product_code": "QR_CODE_OFFLINE",
        }
        if body:
            biz_content["body"] = body
        if user_name:
            biz_content["operator_id"] = user_name[:30]

        try:
            result = await self._request(
                "alipay.trade.precreate",
                biz_content,
                notify_url=notify_url,
            )
            code = result.get("code")
            if code == "10000":
                qr_code = result.get("qr_code")
                return True, "下单成功", qr_code
            else:
                sub_msg = result.get("sub_msg", result.get("msg", "未知错误"))
                return False, f"支付宝下单失败: {sub_msg}", None
        except Exception as e:
            return False, f"支付宝请求异常: {str(e)}", None

    async def query_trade(self, out_trade_no: str) -> Tuple[bool, str, Optional[str]]:
        """
        查询交易状态
        返回: (success, trade_status, message)
        trade_status: WAIT_BUYER_PAY / TRADE_SUCCESS / TRADE_FINISHED / TRADE_CLOSED / None
        """
        if not self.enabled:
            return False, None, "支付宝未配置"

        biz_content = {
            "out_trade_no": out_trade_no,
        }

        try:
            result = await self._request("alipay.trade.query", biz_content)
            code = result.get("code")
            if code == "10000":
                trade_status = result.get("trade_status")
                trade_no = result.get("trade_no")
                return True, trade_status, trade_no
            else:
                # 订单不存在
                sub_code = result.get("sub_code", "")
                if sub_code in ("ACQ.TRADE_NOT_EXIST", "40004"):
                    return True, "WAIT_BUYER_PAY", None
                sub_msg = result.get("sub_msg", result.get("msg", "未知错误"))
                return False, None, f"查询失败: {sub_msg}"
        except Exception as e:
            return False, None, f"查询异常: {str(e)}"

    async def cancel_trade(self, out_trade_no: str) -> bool:
        """撤销交易"""
        if not self.enabled:
            return False

        biz_content = {
            "out_trade_no": out_trade_no,
        }

        try:
            result = await self._request("alipay.trade.cancel", biz_content)
            return result.get("code") == "10000"
        except Exception:
            return False

    def build_page_pay_form(
        self,
        out_trade_no: str,
        total_amount: float,
        subject: str,
        body: str = "",
        return_url: str = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        构建电脑网站支付表单（alipay.trade.page.pay）
        返回: (success, message, form_html)
        前端将form_html插入页面自动提交即可跳转支付宝收银台
        """
        from urllib.parse import urlencode
        
        if not self.enabled:
            return False, "支付宝支付未配置", None

        notify_url = settings.ALIPAY_NOTIFY_URL or f"{settings.SERVER_PUBLIC_URL}/api/payment/alipay/notify"
        return_url = return_url or f"{settings.SERVER_PUBLIC_URL}/payment/return"

        biz_content = {
            "out_trade_no": out_trade_no,
            "total_amount": _format_amount(total_amount),
            "subject": subject,
            "product_code": "FAST_INSTANT_TRADE_PAY",
        }
        if body:
            biz_content["body"] = body

        params = {
            "app_id": self.app_id,
            "method": "alipay.trade.page.pay",
            "charset": self.charset,
            "sign_type": self.sign_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": self.version,
            "biz_content": json.dumps(biz_content, separators=(',', ':'), ensure_ascii=False),
            "notify_url": notify_url,
            "return_url": return_url,
        }

        try:
            params["sign"] = self._sign(params)
        except Exception as e:
            return False, f"签名失败: {str(e)}", None

        # 构建自动提交的表单HTML
        form_inputs = ""
        for k, v in params.items():
            form_inputs += f'<input type="hidden" name="{k}" value="{_html_escape(str(v))}">'
        
        form_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>正在跳转到支付宝...</title>
<style>body{{text-align:center;padding:50px;font-family:sans-serif;}}</style>
</head>
<body>
<p>正在跳转到支付宝收银台，请稍候...</p>
<form id="alipay_submit" name="alipay_submit" action="{self.gateway}" method="post">
{form_inputs}
</form>
<script>document.forms['alipay_submit'].submit();</script>
</body>
</html>"""

        return True, "表单构建成功", form_html

    def activate_pro_for_order(self, db: Session, order: PaymentOrder) -> bool:
        """支付成功后激活用户Pro"""
        if order.activated:
            return True

        user = db.query(UserUsage).filter(UserUsage.name == order.user_name).first()
        if not user:
            return False

        # 计算新的到期时间
        from datetime import timedelta
        now = datetime.utcnow()
        base_expire = user.pro_expire_at if user.is_pro_active() else now
        user.is_pro = True
        user.pro_expire_at = base_expire + timedelta(days=order.duration_days)

        order.status = "TRADE_SUCCESS"
        order.paid_at = now
        order.activated = True

        db.commit()
        return True


# 全局单例
alipay_service = AlipayService()
