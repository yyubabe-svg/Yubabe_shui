from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from datetime import datetime
from app.core.database import Base


class UserUsage(Base):
    """用户使用量与Pro状态"""
    __tablename__ = "user_usages"

    name = Column(String(50), primary_key=True, index=True)
    pin_hash = Column(String(128), nullable=True)  # PIN码哈希（可选）
    is_pro = Column(Boolean, default=False)
    pro_expire_at = Column(DateTime, nullable=True)
    total_upload_bytes = Column(BigInteger, default=0)
    daily_qa_count = Column(Integer, default=0)
    daily_qa_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    iso_used_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)

    def is_pro_active(self) -> bool:
        """检查Pro是否在有效期内"""
        if not self.is_pro:
            return False
        if self.pro_expire_at is None:
            return False
        return self.pro_expire_at > datetime.utcnow()

    def get_daily_qa_remaining(self, daily_limit: int) -> int:
        """获取今日剩余问答次数"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.daily_qa_date != today:
            return daily_limit
        return max(0, daily_limit - self.daily_qa_count)

    def increment_qa_count(self):
        """增加今日问答计数"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.daily_qa_date != today:
            self.daily_qa_count = 1
            self.daily_qa_date = today
        else:
            self.daily_qa_count += 1

    def reset_daily_if_needed(self):
        """如果是新的一天，重置日计数"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.daily_qa_date != today:
            self.daily_qa_count = 0
            self.daily_qa_date = today


class ActivationCode(Base):
    """激活码"""
    __tablename__ = "activation_codes"

    code = Column(String(20), primary_key=True)
    code_type = Column(String(10), nullable=False)  # month / year
    duration_days = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)
    used_by_name = Column(String(50), nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    remark = Column(String(200), nullable=True)
