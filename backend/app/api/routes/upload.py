import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document, FileType, ParseStatus
from app.api.routes.usage import get_current_user, check_feature_access
from app.models.user_usage import UserUsage

router = APIRouter()


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    doc_type: Optional[str] = Form("其他"),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传文件并创建文档记录（需登录，检查额度）"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.md', '.markdown'}
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")
    
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
    
    try:
        contents = await file.read()
        file_size = len(contents)
        
        # 检查文件大小和存储额度（非Mock模式）
        if not settings.MOCK_MODE:
            check = check_feature_access(user, "upload", file_size=file_size, db=db)
            if not check.allowed:
                raise HTTPException(status_code=402, detail=check.reason)
        
        # Mock模式下也检查基础大小限制
        max_allowed = settings.PRO_MAX_FILE_SIZE if user.is_pro_active() else settings.FREE_MAX_FILE_SIZE
        if file_size > max_allowed:
            limit_mb = max_allowed // 1024 // 1024
            raise HTTPException(status_code=400, detail=f"文件大小超过限制({limit_mb}MB)")
        
        with open(file_path, 'wb') as f:
            f.write(contents)
        
        # 创建文档记录
        doc_title = title or os.path.splitext(file.filename)[0]
        
        # 映射doc_type到FileType枚举
        type_map = {
            "水利规范": FileType.STANDARD,
            "历史工程报告": FileType.PROJECT_REPORT,
            "防汛预案": FileType.FLOOD_PLAN,
            "设计说明书": FileType.DESIGN_DOC,
            "审查意见": FileType.REVIEW_OPINION,
            "其他": FileType.OTHER,
        }
        file_type_enum = type_map.get(doc_type, FileType.OTHER)
        
        doc = Document(
            title=doc_title,
            file_type=file_type_enum.value,
            file_path=file_path,
            original_filename=file.filename,
            file_size=file_size,
            upload_user=user.name,
            parse_status=ParseStatus.PENDING.value,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # 累加存储量
        if not settings.MOCK_MODE:
            user.total_upload_bytes += file_size
            db.commit()
        
        return {
            "file_id": file_id,
            "doc_id": doc.id,
            "file_path": file_path,
            "original_filename": file.filename,
            "file_size": file_size,
            "title": doc_title,
            "message": "文件上传成功，请点击解析入库",
        }
    except HTTPException:
        # 清理已保存的文件
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise
    except Exception as e:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
