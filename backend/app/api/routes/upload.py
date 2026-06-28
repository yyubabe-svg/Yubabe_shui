import os
import uuid
import asyncio
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request
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
    request: Request = None,
):
    """上传文件并创建文档记录（需登录，检查额度）- 修复13：aiofiles异步写入、修复裸except、移除绝对路径"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    # 修复13：移除.doc格式支持（python-docx无法解析）
    allowed_extensions = {'.pdf', '.docx', '.txt', '.md', '.markdown', '.xlsx', '.xls'}
    if file_ext == '.doc':
        raise HTTPException(status_code=400, detail=".doc格式不支持，请转换为.docx后再上传")
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")
    
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
    
    # 修复13：先检查Content-Length头部，避免读取大文件到内存后才发现超限
    content_length = 0
    if request and "content-length" in request.headers:
        try:
            content_length = int(request.headers["content-length"])
        except (ValueError, TypeError):
            pass
    
    max_allowed = settings.PRO_MAX_FILE_SIZE if user.is_pro_active() else settings.FREE_MAX_FILE_SIZE
    
    if content_length > 0 and content_length > max_allowed:
        limit_mb = max_allowed // 1024 // 1024
        raise HTTPException(status_code=400, detail=f"文件大小超过限制({limit_mb}MB)")
    
    try:
        # 修复13：使用aiofiles异步流式写入，避免一次性read到内存
        file_size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            # 分块读取并写入
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
                file_size += len(chunk)
                # 写入过程中检查大小限制
                if file_size > max_allowed:
                    limit_mb = max_allowed // 1024 // 1024
                    raise HTTPException(status_code=400, detail=f"文件大小超过限制({limit_mb}MB)")
        
        # 检查文件大小和存储额度（非Mock模式）
        if not settings.MOCK_MODE:
            check = check_feature_access(user, "upload", file_size=file_size, db=db)
            if not check.allowed:
                # 清理文件
                if os.path.exists(file_path):
                    await _safe_remove(file_path)
                raise HTTPException(status_code=402, detail=check.reason)
        
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
        
        # 修复13：返回值中移除file_path绝对路径（安全考虑）
        return {
            "file_id": file_id,
            "doc_id": doc.id,
            "original_filename": file.filename,
            "file_size": file_size,
            "title": doc_title,
            "message": "文件上传成功，请点击解析入库",
        }
    except HTTPException:
        # 清理已保存的文件
        await _safe_remove(file_path)
        raise
    except Exception as e:
        await _safe_remove(file_path)
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")


async def _safe_remove(path: str):
    """安全删除文件（修复13：使用asyncio.to_thread包裹同步os.remove，修复裸except）"""
    if os.path.exists(path):
        try:
            await asyncio.to_thread(os.remove, path)
        except Exception:
            # 修复13：不再使用裸except
            pass
