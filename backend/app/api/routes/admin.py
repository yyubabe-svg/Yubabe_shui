from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from pydantic import BaseModel
from app.core.database import get_db
from app.models.document import Document, Chunk
from app.models.qa_log import QALog
from app.models.payment import PaymentOrder
from app.models.user_usage import UserUsage, ActivationCode
from app.core.config import settings
from app.services.vector_store import vector_store

router = APIRouter()


class ActivateUserRequest(BaseModel):
    user_name: str
    days: int = 365
    note: str = "管理员手动激活"


@router.post("/activate-user")
async def admin_activate_user(
    req: ActivateUserRequest,
    x_admin_token: str = Header(None),
    db: Session = Depends(get_db),
):
    """管理员手动激活用户Pro（收到转账后使用）"""
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="管理员权限不足")
    
    user = db.query(UserUsage).filter(UserUsage.name == req.user_name).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    now = datetime.utcnow()
    base_expire = user.pro_expire_at if user.is_pro_active() else now
    user.is_pro = True
    user.pro_expire_at = base_expire + timedelta(days=req.days)
    
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"已成功为用户 {req.user_name} 激活Pro",
        "user_name": user.name,
        "is_pro": True,
        "pro_expire_at": user.pro_expire_at.strftime("%Y-%m-%d"),
        "days": req.days,
    }


@router.get("/users")
async def get_users(
    x_admin_token: str = Header(None),
    db: Session = Depends(get_db),
):
    """获取用户列表（管理员）"""
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="管理员权限不足")
    
    users = db.query(UserUsage).order_by(UserUsage.created_at.desc()).all()
    return {
        "users": [
            {
                "name": u.name,
                "is_pro": u.is_pro_active(),
                "pro_expire_at": u.pro_expire_at.strftime("%Y-%m-%d") if u.pro_expire_at else None,
                "total_upload_bytes": u.total_upload_bytes,
                "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else None,
                "last_active_at": u.last_active_at.strftime("%Y-%m-%d %H:%M") if u.last_active_at else None,
            }
            for u in users
        ]
    }


@router.get("/orders")
async def get_orders(
    x_admin_token: str = Header(None),
    db: Session = Depends(get_db),
):
    """获取支付订单列表（管理员）"""
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="管理员权限不足")
    
    orders = db.query(PaymentOrder).order_by(PaymentOrder.created_at.desc()).limit(50).all()
    return {
        "orders": [
            {
                "out_trade_no": o.out_trade_no,
                "user_name": o.user_name,
                "amount": o.amount / 100,
                "plan_type": o.plan_type,
                "status": o.status,
                "activated": o.activated,
                "created_at": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else None,
                "paid_at": o.paid_at.strftime("%Y-%m-%d %H:%M") if o.paid_at else None,
            }
            for o in orders
        ]
    }


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """获取系统统计"""
    total_docs = db.query(Document).count()
    today = date.today()
    qa_today = db.query(QALog).filter(
        QALog.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    total_users = db.query(UserUsage).count()
    pro_users = db.query(UserUsage).filter(UserUsage.is_pro == True).count()
    
    # 今日活跃用户（last_active_at 是今天）
    active_today = db.query(UserUsage).filter(
        UserUsage.last_active_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    # 文档类型分布
    docs_by_type = {}
    docs = db.query(Document).all()
    for doc in docs:
        t = doc.file_type if doc.file_type else "其他"
        docs_by_type[t] = docs_by_type.get(t, 0) + 1
    
    # 最近上传
    recent_uploads = db.query(Document).order_by(Document.created_at.desc()).limit(5).all()
    recent_upload_list = [
        {"title": d.title, "file_type": d.file_type if d.file_type else None, "created_at": d.created_at.isoformat() if d.created_at else None}
        for d in recent_uploads
    ]
    
    # 最近问答
    recent_qa = db.query(QALog).order_by(QALog.created_at.desc()).limit(5).all()
    recent_qa_list = [
        {"question": q.question[:50], "created_at": q.created_at.isoformat() if q.created_at else None}
        for q in recent_qa
    ]
    
    return {
        "total_documents": total_docs,
        "total_qa_today": qa_today,
        "total_users": total_users,
        "pro_users": pro_users,
        "active_today": active_today,
        "documents_by_type": docs_by_type,
        "recent_uploads": recent_upload_list,
        "recent_qa": recent_qa_list,
        "vector_count": vector_store.count(),
    }


@router.get("/model-config")
async def get_model_config():
    """获取模型配置"""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "mock_mode": settings.MOCK_MODE,
        "free_daily_qa": settings.FREE_DAILY_QA,
        "free_max_file_size_mb": settings.FREE_MAX_FILE_SIZE // 1024 // 1024,
        "pro_max_file_size_mb": settings.PRO_MAX_FILE_SIZE // 1024 // 1024,
        "price_monthly": settings.PRICE_MONTHLY,
        "price_yearly": settings.PRICE_YEARLY,
    }


@router.post("/model-config")
async def update_model_config(config: dict):
    """更新模型配置（MVP需要重启生效）"""
    return {"message": "配置已更新，需要重启服务生效"}


@router.post("/knowledge/rebuild")
async def rebuild_knowledge(db: Session = Depends(get_db)):
    """重建知识库向量索引"""
    from app.models.document import ParseStatus
    from app.services.document_parser import document_parser
    from app.services.embedding import embedding_service
    
    vector_store.clear()
    
    docs = db.query(Document).filter(Document.parse_status == ParseStatus.COMPLETED.value).all()
    total_chunks = 0
    
    for doc in docs:
        if not doc.file_path:
            continue
        
        db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
        db.commit()
        
        chunks_data = document_parser.parse_and_chunk(doc.file_path, doc.id, doc.title)
        
        saved_chunks = []
        texts_to_embed = []
        
        for chunk_data in chunks_data:
            chunk = Chunk(**chunk_data)
            db.add(chunk)
            saved_chunks.append(chunk)
            texts_to_embed.append(chunk_data["chunk_text"])
        
        db.flush()
        
        embeddings = embedding_service.embed(texts_to_embed)
        vector_items = []
        
        for chunk, embedding in zip(saved_chunks, embeddings):
            vector_id = f"chunk_{chunk.id}"
            chunk.embedding_id = vector_id
            vector_items.append({
                "id": vector_id,
                "embedding": embedding,
                "metadata": {
                    "document_id": doc.id,
                    "chunk_id": chunk.id,
                    "file_name": doc.title,
                    "text": chunk.chunk_text[:200],
                },
            })
        
        vector_store.add_batch(vector_items)
        total_chunks += len(saved_chunks)
    
    db.commit()
    return {"message": "知识库重建完成", "total_chunks": total_chunks}
