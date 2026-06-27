import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
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
from datetime import datetime

router = APIRouter()


@router.post("/upload")
async def upload_review_file(
    file: UploadFile = File(...),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传待审查文件（需登录）"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.pdf', '.doc', '.docx']:
        raise HTTPException(status_code=400, detail="仅支持PDF/Word格式")
    
    saved_filename = f"review_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
    
    try:
        contents = await file.read()
        file_size = len(contents)
        
        # 检查文件大小（免费版5MB，Pro版50MB）
        max_allowed = settings.PRO_MAX_FILE_SIZE if user.is_pro_active() else settings.FREE_MAX_FILE_SIZE
        if file_size > max_allowed:
            limit_mb = max_allowed // 1024 // 1024
            raise HTTPException(status_code=400, detail=f"文件大小超过限制({limit_mb}MB)")
        
        with open(file_path, 'wb') as f:
            f.write(contents)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    return {"file_path": file_path, "file_name": file.filename, "message": "上传成功"}


@router.post("/analyze")
async def analyze_document(
    request: dict,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分析文档进行合规审查（Pro专属）"""
    # 检查Pro权限（Mock模式不限制）
    if not settings.MOCK_MODE:
        check = check_feature_access(user, "review", db=db)
        if not check.allowed:
            raise HTTPException(status_code=402, detail=check.reason)
    
    file_path = request.get("file_path")
    file_name = request.get("file_name", "")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="文件不存在")
    
    # 解析文档
    doc_text = document_parser.parse(file_path)
    
    # 检索相关规范
    query_embedding = embedding_service.embed_query("水利工程设计规范 强制性条文")
    retrieved = vector_store.search(query_embedding, top_k=3)
    context_chunks = [{"text": r.get("metadata", {}).get("text", ""), "file_name": r.get("metadata", {}).get("file_name", "")} for r in retrieved]
    
    # LLM审查
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
