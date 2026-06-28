import asyncio
import os
import uuid
from datetime import datetime

import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.services.document_parser import document_parser
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.models.review_report import ReviewReport
from app.models.user_usage import UserUsage
from app.api.routes.usage import get_current_user, check_feature_access

router = APIRouter()


async def _safe_remove_review_file(path: str):
    """安全删除临时文件"""
    if os.path.exists(path):
        try:
            await asyncio.to_thread(os.remove, path)
        except Exception:
            pass


@router.post("/upload")
async def upload_review_file(
    file: UploadFile = File(...),
    request: Request = None,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传待审查文件（aiofiles异步分块写入，移除.doc，返回文件ID而非绝对路径）"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    # 移除.doc格式支持
    allowed_extensions = {'.pdf', '.docx'}
    if file_ext == '.doc':
        raise HTTPException(status_code=400, detail=".doc格式不支持，请转换为.docx后再上传")
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"仅支持PDF/Word(.docx)格式，不支持{file_ext}")
    
    file_id = str(uuid.uuid4())
    saved_filename = f"review_{file_id}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
    
    # 检查Content-Length
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
    
    file_size = 0
    try:
        # 使用aiofiles异步分块写入
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)
                file_size += len(chunk)
                if file_size > max_allowed:
                    limit_mb = max_allowed // 1024 // 1024
                    raise HTTPException(status_code=400, detail=f"文件大小超过限制({limit_mb}MB)")
    except HTTPException:
        await _safe_remove_review_file(file_path)
        raise
    except Exception as e:
        await _safe_remove_review_file(file_path)
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 不返回绝对file_path，改用文件ID
    return {
        "file_id": file_id,
        "file_name": file.filename,
        "file_size": file_size,
        "message": "上传成功"
    }


def _get_review_file_path(file_id: str, file_ext: str = ".docx") -> str:
    """根据file_id获取文件路径（内部使用，不暴露给前端）"""
    # 注意：前端需要同时传file_id和file_ext来定位文件
    # 为简化，我们遍历查找
    upload_dir = settings.UPLOAD_DIR
    for ext in ['.pdf', '.docx']:
        candidate = os.path.join(upload_dir, f"review_{file_id}{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


@router.post("/analyze")
async def analyze_document(
    request: dict,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分析文档进行合规审查（Pro专属）- 添加try/except错误处理，同步操作用asyncio.to_thread包裹"""
    try:
        # 检查Pro权限（Mock模式不限制）
        if not settings.MOCK_MODE:
            check = check_feature_access(user, "review", db=db)
            if not check.allowed:
                raise HTTPException(status_code=402, detail=check.reason)
        
        file_id = request.get("file_id")
        file_name = request.get("file_name", "")
        file_ext = request.get("file_ext", ".docx")
        
        if not file_id:
            # 兼容旧版：如果传的是file_path，尝试从路径中提取信息
            file_path = request.get("file_path")
            if file_path and os.path.exists(file_path):
                pass  # 使用传入的file_path（向后兼容）
            else:
                raise HTTPException(status_code=400, detail="请提供file_id")
        else:
            file_path = _get_review_file_path(file_id, file_ext)
            if not file_path or not os.path.exists(file_path):
                raise HTTPException(status_code=400, detail="文件不存在，请重新上传")
        
        # 解析文档（同步操作用to_thread包裹）
        doc_text = await asyncio.to_thread(document_parser.parse, file_path)
        
        # 检索相关规范（同步操作用to_thread包裹）
        query_embedding = await asyncio.to_thread(
            embedding_service.embed_query, "水利工程设计规范 强制性条文"
        )
        retrieved = await asyncio.to_thread(vector_store.search, query_embedding, 3)
        context_chunks = [
            {
                "text": r.get("metadata", {}).get("text", "") or r.get("metadata", {}).get("content", ""),
                "file_name": r.get("metadata", {}).get("file_name", "")
            }
            for r in retrieved
        ]
        
        # LLM审查（已经是async方法）
        review_text = await llm_service.review_document(doc_text[:5000], context_chunks)
        
        # 保存报告
        report = ReviewReport(
            file_name=file_name,
            review_text=review_text,
            created_at=datetime.utcnow(),
        )
        db.add(report)
        db.commit()
        report_id = report.id
        
        return {
            "report_id": report_id,
            "project_name": "设计说明书",
            "review_text": review_text,
            "params": [],
            "issues": [],
            "suggestions": [],
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"文档分析失败: {str(e)}")


@router.get("/{report_id}")
async def get_review_report(
    report_id: int,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取审查报告"""
    report = db.query(ReviewReport).filter(ReviewReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {
        "id": report.id,
        "file_name": report.file_name,
        "review_text": report.review_text,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
