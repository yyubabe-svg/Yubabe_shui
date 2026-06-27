import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.document import Document, Chunk, FileType, ParseStatus
from app.models.user_usage import UserUsage
from app.api.routes.usage import get_current_user
from app.schemas.document import DocumentResponse, DocumentDetail, ChunkResponse
from app.services.document_parser import document_parser
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=list)
async def list_documents(
    file_type: Optional[str] = None,
    department: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取文档列表（公开，知识库共享）"""
    query = db.query(Document)
    
    if file_type:
        query = query.filter(Document.file_type == file_type)
    if department:
        query = query.filter(Document.department == department)
    if keyword:
        query = query.filter(Document.title.contains(keyword))
    
    total = query.count()
    docs = query.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "file_type": doc.file_type if doc.file_type else None,
            "project_name": doc.project_name,
            "river_basin": doc.river_basin,
            "department": doc.department,
            "security_level": doc.security_level if doc.security_level else None,
            "original_filename": doc.original_filename,
            "file_size": doc.file_size,
            "parse_status": doc.parse_status if doc.parse_status else None,
            "chunk_count": doc.chunk_count,
            "upload_user": doc.upload_user,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


@router.get("/{doc_id}")
async def get_document(doc_id: int, db: Session = Depends(get_db)):
    """获取文档详情（公开）"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {
        "id": doc.id,
        "title": doc.title,
        "file_type": doc.file_type if doc.file_type else None,
        "project_name": doc.project_name,
        "parse_status": doc.parse_status if doc.parse_status else None,
        "file_size": doc.file_size,
        "upload_user": doc.upload_user,
    }


@router.get("/{doc_id}/chunks")
async def get_document_chunks(doc_id: int, db: Session = Depends(get_db)):
    """获取文档分块（公开）"""
    chunks = db.query(Chunk).filter(Chunk.document_id == doc_id).all()
    return [
        {
            "id": c.id,
            "chunk_text": c.chunk_text,
            "page_number": c.page_number,
            "section_title": c.section_title,
        }
        for c in chunks
    ]


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除文档（需登录）"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    file_size = doc.file_size or 0
    
    # 删除向量
    vector_store.delete_by_document(doc_id)
    
    # 删除物理文件
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    
    db.delete(doc)
    db.commit()
    
    # 扣减存储量（非Mock模式）
    if not settings.MOCK_MODE and file_size > 0:
        user.total_upload_bytes = max(0, user.total_upload_bytes - file_size)
        db.commit()
    
    return {"message": "删除成功"}


@router.post("/{doc_id}/parse")
async def parse_document(
    doc_id: int,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解析文档并入库（需登录，存储已在上传时累加）"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=400, detail="文件不存在")
    
    doc.parse_status = ParseStatus.PARSING.value
    db.commit()
    
    try:
        # 解析分块
        chunks_data = document_parser.parse_and_chunk(doc.file_path, doc.id, doc.title)
        
        # 删除旧的chunks和向量
        db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
        vector_store.delete_by_document(doc_id)
        db.commit()
        
        # 保存chunks
        texts_to_embed = []
        saved_chunks = []
        
        for chunk_data in chunks_data:
            chunk = Chunk(**chunk_data)
            db.add(chunk)
            saved_chunks.append(chunk)
            texts_to_embed.append(chunk_data["chunk_text"])
        
        db.flush()
        
        # 向量化
        embeddings = embedding_service.embed(texts_to_embed)
        
        vector_items = []
        for chunk, embedding in zip(saved_chunks, embeddings):
            vector_id = f"chunk_{chunk.id}"
            chunk.embedding_id = vector_id
            vector_items.append({
                "id": vector_id,
                "embedding": embedding,
                "metadata": {
                    "document_id": doc_id,
                    "project_id": doc.project_id,
                    "file_type": doc.file_type,
                    "chunk_id": chunk.id,
                    "file_name": doc.title,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "chapter_path": chunk.chapter_path,
                    "text": chunk.chunk_text[:200],
                },
            })
        
        vector_store.add_batch(vector_items)
        
        doc.parse_status = ParseStatus.COMPLETED.value
        doc.chunk_count = len(saved_chunks)
        db.commit()
        
        return {"message": "解析完成", "chunk_count": len(saved_chunks)}
    except Exception as e:
        doc.parse_status = ParseStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
