import asyncio
import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.qa_log import QALog
from app.models.user_usage import UserUsage
from app.schemas.qa import QARequest, QAResponse, QAFeedback
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service, RAG_PROMPT_TEMPLATE
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
    
    # 向量化问题（使用asyncio.to_thread避免阻塞事件循环）
    query_embedding = await asyncio.to_thread(embedding_service.embed_query, request.question)
    
    # 向量检索
    results = await asyncio.to_thread(vector_store.search, query_embedding, request.top_k)
    
    # 构建检索结果
    sources = []
    context_chunks = []
    for r in results:
        meta = r.get("metadata", {})
        source = {
            "file_name": meta.get("file_name", "未知"),
            "page_number": meta.get("page_number"),
            "section_title": meta.get("section_title"),
            "text": meta.get("text", "") or meta.get("content", ""),
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


@router.post("/stream")
async def query_qa_stream(
    request: QARequest,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """知识库问答（SSE流式）"""
    # 检查额度
    if not settings.MOCK_MODE:
        check = check_feature_access(user, "qa", db=db)
        if not check.allowed:
            raise HTTPException(status_code=402, detail=check.reason)
    
    async def event_generator():
        try:
            # 向量化和检索（用to_thread避免阻塞）
            query_embedding = await asyncio.to_thread(embedding_service.embed_query, request.question)
            results = await asyncio.to_thread(vector_store.search, query_embedding, request.top_k)
            
            sources = []
            context_chunks = []
            for r in results:
                meta = r.get("metadata", {})
                source = {
                    "file_name": meta.get("file_name", "未知"),
                    "page_number": meta.get("page_number"),
                    "section_title": meta.get("section_title"),
                    "text": meta.get("text", "") or meta.get("content", ""),
                    "score": r.get("score", 0),
                }
                sources.append(source)
                context_chunks.append(source)
            
            # 发送sources事件
            yield {"event": "sources", "data": json.dumps(sources, ensure_ascii=False)}
            
            # 构建prompt（使用.replace而非.format，避免用户输入中花括号导致异常）
            context = llm_service._format_context(context_chunks)
            prompt = RAG_PROMPT_TEMPLATE.replace("{question}", request.question).replace("{context}", context)
            
            # 流式调用LLM
            full_answer = []
            messages = [{"role": "user", "content": prompt}]
            async for chunk in llm_service.chat_stream(messages):
                full_answer.append(chunk)
                yield {"event": "token", "data": json.dumps({"content": chunk}, ensure_ascii=False)}
            
            # 保存日志
            answer = "".join(full_answer)
            
            # 计数+1
            if not settings.MOCK_MODE:
                user.increment_qa_count()
            
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
            
            yield {"event": "done", "data": json.dumps({"content": answer}, ensure_ascii=False)}
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {"event": "error", "data": json.dumps({"error": str(e)}, ensure_ascii=False)}
    
    return EventSourceResponse(event_generator())


@router.post("/feedback")
async def submit_feedback(
    feedback: QAFeedback,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交问答反馈（需要认证）"""
    log = db.query(QALog).filter(QALog.id == feedback.log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    # 只能反馈自己的日志
    if log.user_name != user.name:
        raise HTTPException(status_code=403, detail="无权操作他人的日志")
    log.feedback = feedback.feedback
    db.commit()
    return {"message": "反馈已提交"}


@router.get("/logs")
async def get_qa_logs(
    scenario_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的问答历史（按用户过滤）"""
    query = db.query(QALog).filter(QALog.user_name == user.name)
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
