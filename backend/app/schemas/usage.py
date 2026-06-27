from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """注册/登录请求"""
    name: str = Field(..., min_length=2, max_length=20, description="姓名")
    pin: Optional[str] = Field(None, min_length=4, max_length=6, description="4-6位PIN码")
    is_new_pin: bool = Field(False, description="是否是新设置PIN")


class ActivateRequest(BaseModel):
    """激活码激活请求"""
    code: str = Field(..., min_length=10, max_length=25)


class SetPinRequest(BaseModel):
    """设置PIN请求"""
    old_pin: Optional[str] = None
    new_pin: str = Field(..., min_length=4, max_length=6)


class UsageResponse(BaseModel):
    """使用量状态响应"""
    name: str
    is_pro: bool
    pro_expire_at: Optional[datetime] = None
    pro_days_remaining: Optional[int] = None
    total_upload_bytes: int
    total_storage_limit: int
    daily_qa_count: int
    daily_qa_limit: int
    daily_qa_remaining: int
    iso_used_count: int
    iso_free_limit: int
    has_pin: bool


class FeatureCheckResponse(BaseModel):
    """功能权限检查响应"""
    allowed: bool
    feature: str
    reason: Optional[str] = None
    current: Optional[int] = None
    limit: Optional[int] = None
    is_pro: bool = False
