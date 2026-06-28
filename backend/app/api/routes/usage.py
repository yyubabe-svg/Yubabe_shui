import hashlib
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.user_usage import UserUsage, ActivationCode
from app.schemas.usage import (
    RegisterRequest, ActivateRequest, SetPinRequest,
    UsageResponse, FeatureCheckResponse,
)

# 用户名验证正则：允许中文、英文、数字、下划线，长度2-20
USERNAME_PATTERN = re.compile(r'^[\u4e00-\u9fa5a-zA-Z0-9_]{2,20}$')

router = APIRouter()


def hash_pin(pin: str) -> str:
    """PIN码哈希（简单hash，非高安全场景足够）"""
    return hashlib.sha256(f"shushui-{pin}".encode()).hexdigest()


def get_current_user(
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    x_username: Optional[str] = Header(None, alias="X-Username"),
    db: Session = Depends(get_db),
) -> UserUsage:
    """从请求头获取当前用户，不存在则自动创建（容错）"""
    user_name = x_user_name or x_username
    if not user_name or not user_name.strip():
        raise HTTPException(status_code=401, detail="未登录，请先输入姓名")
    
    # URL解码（处理中文用户名被URL编码的情况）
    user_name = unquote(user_name)
    # 去除首尾空格
    user_name = user_name.strip()
    
    # 用户名格式验证：只允许中文、英文、数字、下划线，长度2-20
    if not USERNAME_PATTERN.match(user_name):
        raise HTTPException(status_code=400, detail="用户名格式不正确，只允许中文、英文、数字、下划线，长度2-20位")
    
    user = db.query(UserUsage).filter(UserUsage.name == user_name).first()
    if not user:
        # 用户不存在，自动创建（避免公网环境下header异常导致401）
        print(f"[Auth] User {user_name} not found in get_current_user, auto-creating...")
        user = UserUsage(
            name=user_name,
            pin_hash=None,
            is_pro=False,
            total_upload_bytes=0,
            daily_qa_count=0,
            daily_qa_date=datetime.utcnow().strftime("%Y-%m-%d"),
            iso_used_count=0,
            pro_expire_at=None,
            created_at=datetime.utcnow(),
            last_active_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    user.last_active_at = datetime.utcnow()
    user.reset_daily_if_needed()
    db.commit()
    return user


def _build_usage_response(user: UserUsage) -> UsageResponse:
    """构建使用量响应"""
    is_pro = user.is_pro_active()
    storage_limit = settings.PRO_TOTAL_STORAGE if is_pro else settings.FREE_TOTAL_STORAGE
    qa_limit = 999999 if is_pro else settings.FREE_DAILY_QA
    iso_limit = 999999 if is_pro else settings.FREE_ISO_TRIES
    pro_days = None
    if is_pro and user.pro_expire_at:
        pro_days = max(0, (user.pro_expire_at - datetime.utcnow()).days)
    return UsageResponse(
        name=user.name,
        is_pro=is_pro,
        pro_expire_at=user.pro_expire_at,
        pro_days_remaining=pro_days,
        total_upload_bytes=user.total_upload_bytes,
        total_storage_limit=storage_limit,
        daily_qa_count=user.daily_qa_count,
        daily_qa_limit=qa_limit,
        daily_qa_remaining=user.get_daily_qa_remaining(settings.FREE_DAILY_QA) if not is_pro else qa_limit,
        iso_used_count=user.iso_used_count,
        iso_free_limit=iso_limit,
        has_pin=bool(user.pin_hash),
    )


def check_feature_access(
    user: UserUsage,
    feature: str,
    file_size: int = 0,
    db: Session = None,
) -> FeatureCheckResponse:
    """
    检查功能权限，返回 FeatureCheckResponse。
    feature: qa / upload / iso / review / storage
    """
    is_pro = user.is_pro_active()

    if feature == "qa":
        if is_pro:
            return FeatureCheckResponse(allowed=True, feature=feature, is_pro=True)
        if user.get_daily_qa_remaining(settings.FREE_DAILY_QA) <= 0:
            return FeatureCheckResponse(
                allowed=False, feature=feature,
                reason=f"今日免费问答次数已用完（{settings.FREE_DAILY_QA}次/天），升级Pro不限次数",
                current=user.daily_qa_count, limit=settings.FREE_DAILY_QA, is_pro=False,
            )
        return FeatureCheckResponse(allowed=True, feature=feature, is_pro=False)

    if feature == "upload":
        max_file = settings.PRO_MAX_FILE_SIZE if is_pro else settings.FREE_MAX_FILE_SIZE
        if file_size > max_file:
            limit_mb = max_file // 1024 // 1024
            return FeatureCheckResponse(
                allowed=False, feature=feature,
                reason=f"文件大小超限，{'Pro版' if is_pro else '免费版'}单文件上限{limit_mb}MB",
                current=file_size, limit=max_file, is_pro=is_pro,
            )
        max_storage = settings.PRO_TOTAL_STORAGE if is_pro else settings.FREE_TOTAL_STORAGE
        if user.total_upload_bytes + file_size > max_storage:
            return FeatureCheckResponse(
                allowed=False, feature=feature,
                reason="存储空间不足，请升级Pro或删除部分文档",
                current=user.total_upload_bytes + file_size, limit=max_storage, is_pro=is_pro,
            )
        return FeatureCheckResponse(allowed=True, feature=feature, is_pro=is_pro)

    if feature == "iso":
        if is_pro:
            return FeatureCheckResponse(allowed=True, feature=feature, is_pro=True)
        if user.iso_used_count >= settings.FREE_ISO_TRIES:
            return FeatureCheckResponse(
                allowed=False, feature=feature,
                reason=f"ISO文档免费体验次数已用完（{settings.FREE_ISO_TRIES}次），升级Pro无限使用",
                current=user.iso_used_count, limit=settings.FREE_ISO_TRIES, is_pro=False,
            )
        return FeatureCheckResponse(allowed=True, feature=feature, is_pro=False)

    if feature == "review":
        if is_pro:
            return FeatureCheckResponse(allowed=True, feature=feature, is_pro=True)
        return FeatureCheckResponse(
            allowed=False, feature=feature,
            reason="合规审查为Pro专属功能，升级后可使用",
            is_pro=False,
        )

    return FeatureCheckResponse(allowed=True, feature=feature, is_pro=is_pro)


@router.post("/register", response_model=UsageResponse, summary="注册/登录（输入姓名）")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """首次使用时输入姓名注册，已存在则验证PIN"""
    name = req.name.strip()
    if not name or len(name) < 1:
        raise HTTPException(status_code=400, detail="请输入姓名")
    
    # 用户名格式验证
    if not USERNAME_PATTERN.match(name):
        raise HTTPException(status_code=400, detail="用户名格式不正确，只允许中文、英文、数字、下划线，长度2-20位")

    existing = db.query(UserUsage).filter(UserUsage.name == name).first()

    if existing:
        # 已存在用户：验证PIN
        if existing.pin_hash:
            if not req.pin:
                raise HTTPException(status_code=403, detail="该姓名已设置PIN，请输入PIN验证")
            if hash_pin(req.pin) != existing.pin_hash:
                raise HTTPException(status_code=403, detail="PIN码错误")
        # PIN验证通过，更新活跃时间
        existing.last_active_at = datetime.utcnow()
        existing.reset_daily_if_needed()
        db.commit()
        db.refresh(existing)
        return _build_usage_response(existing)

    # 新用户
    pin_hash = hash_pin(req.pin) if req.pin and req.is_new_pin else None
    user = UserUsage(
        name=name,
        pin_hash=pin_hash,
        is_pro=False,
        total_upload_bytes=0,
        daily_qa_count=0,
        daily_qa_date=datetime.utcnow().strftime("%Y-%m-%d"),
        iso_used_count=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_usage_response(user)


@router.get("/status", response_model=UsageResponse, summary="获取当前用户使用状态")
async def get_status(user: UserUsage = Depends(get_current_user)):
    return _build_usage_response(user)


@router.post("/activate", response_model=UsageResponse, summary="使用激活码升级Pro")
async def activate_pro(req: ActivateRequest, user: UserUsage = Depends(get_current_user), db: Session = Depends(get_db)):
    code = req.code.strip().upper()
    activation = db.query(ActivationCode).filter(ActivationCode.code == code).first()
    if not activation:
        raise HTTPException(status_code=400, detail="激活码无效")
    if activation.is_used:
        raise HTTPException(status_code=400, detail="该激活码已被使用")

    # 激活
    now = datetime.utcnow()
    base_expire = user.pro_expire_at if user.is_pro_active() else now
    new_expire = base_expire + timedelta(days=activation.duration_days)

    activation.is_used = True
    activation.used_by_name = user.name
    activation.used_at = now

    user.is_pro = True
    user.pro_expire_at = new_expire

    db.commit()
    db.refresh(user)
    return _build_usage_response(user)


@router.post("/set-pin", response_model=UsageResponse, summary="设置/修改PIN码")
async def set_pin(req: SetPinRequest, user: UserUsage = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.pin_hash and req.old_pin:
        if hash_pin(req.old_pin) != user.pin_hash:
            raise HTTPException(status_code=400, detail="原PIN码错误")
    user.pin_hash = hash_pin(req.new_pin)
    db.commit()
    db.refresh(user)
    return _build_usage_response(user)


@router.get("/check", response_model=FeatureCheckResponse, summary="检查功能权限")
async def check_feature(
    feature: str = Query(..., description="功能名: qa/upload/iso/review"),
    file_size: int = Query(0, ge=0, description="文件大小(bytes)，仅upload用"),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return check_feature_access(user, feature, file_size, db)


@router.post("/increment-qa", summary="问答计数+1（内部接口）")
async def increment_qa(user: UserUsage = Depends(get_current_user), db: Session = Depends(get_db)):
    user.increment_qa_count()
    db.commit()
    return {"daily_qa_count": user.daily_qa_count}


@router.post("/increment-iso", summary="ISO使用计数+1（内部接口）")
async def increment_iso(user: UserUsage = Depends(get_current_user), db: Session = Depends(get_db)):
    # 检查权限
    check = check_feature_access(user, "iso", db=db)
    if not check.allowed:
        raise HTTPException(status_code=402, detail=check.reason)
    user.iso_used_count += 1
    db.commit()
    return {"iso_used_count": user.iso_used_count}


@router.post("/increment-storage", summary="存储量累加（内部接口）")
async def increment_storage(
    bytes_added: int = Query(..., gt=0),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 检查权限
    check = check_feature_access(user, "upload", file_size=bytes_added, db=db)
    if not check.allowed:
        raise HTTPException(status_code=402, detail=check.reason)
    user.total_upload_bytes += bytes_added
    db.commit()
    return {"total_upload_bytes": user.total_upload_bytes}
