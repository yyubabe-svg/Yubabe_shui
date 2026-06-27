from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.core.database import get_db
from app.models.qa_log import QALog
from app.models.user_usage import UserUsage
from app.schemas.qa import QARequest, QAResponse, QAFeedback
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.api.routes.usage import get_current_user, check_feature_access
from app.core.config import settings

router = APIRouter()


@router.post("/query", response_model=QAResponse)
async def query_qa(
    request: QARequest,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """知识库问答"""
    # 检查问答次数（Mock模式下不限制）
    if not settings.MOCK_MODE:
        check = check_feature_access(user, "qa", db=db)
        if not check.allowed:
            raise HTTPException(status_code=402, detail=check.reason)
    
    # 向量化问题
    query_embedding = embedding_service.embed_query(request.question)
    
    # 向量检索
    results = vector_store.search(query_embedding, top_k=request.top_k)
    
    # 构建检索结果
    sources = []
    context_chunks = []
    for r in results:
        meta = r.get("metadata", {})
        source = {
            "file_name": meta.get("file_name", "未知"),
            "page_number": meta.get("page_number"),
            "section_title": meta.get("section_title"),
            "text": meta.get("text", ""),
            "score": r.get("score", 0),
        }
        sources.append(source)
        context_chunks.append(source)
    
    # LLM生成回答
    answer = await llm_service.rag_query(request.question, context_chunks)
    
    # 计数+1
    if not settings.MOCK_MODE:
        user.increment_qa_count()
    
    # 保存日志
    qa_log = QALog(
        user_name=user.name,
        question=request.question,
        answer=answer,
        sources_json=[s["file_name"] for s in sources],
        scenario_type=request.scenario_type,
        created_at=datetime.utcnow(),
    )
    db.add(qa_log)
    db.commit()
    
    return QAResponse(
        answer=answer,
        sources=sources,
        scenario_type=request.scenario_type,
    )


@router.post("/feedback")
async def submit_feedback(feedback: QAFeedback, db: Session = Depends(get_db)):
    """提交问答反馈"""
    log = db.query(QALog).filter(QALog.id == feedback.log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    log.feedback = feedback.feedback
    db.commit()
    return {"message": "反馈已提交"}


@router.get("/logs")
async def get_qa_logs(
    scenario_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取问答历史"""
    query = db.query(QALog)
    if scenario_type:
        query = query.filter(QALog.scenario_type == scenario_type)
    
    logs = query.order_by(QALog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return [
        {
            "id": log.id,
            "question": log.question,
            "answer": log.answer[:200] if log.answer else "",
            "scenario_type": log.scenario_type,
            "feedback": log.feedback,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
