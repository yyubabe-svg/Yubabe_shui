"""统一检索服务：向量+关键词混合检索、项目维度优先、上下文组装"""
from typing import List, Dict, Any, Optional
from app.services.vector_store import vector_store
from app.services.embedding import embedding_service


class RetrievedChunk:
    """检索结果块"""
    def __init__(self, chunk_text: str, document_id: int, document_title: str = "",
                 page_number: int = None, section_title: str = "",
                 chapter_path: str = "", score: float = 0.0,
                 tables_json: Any = None):
        self.chunk_text = chunk_text
        self.document_id = document_id
        self.document_title = document_title
        self.page_number = page_number
        self.section_title = section_title
        self.chapter_path = chapter_path
        self.score = score
        self.tables_json = tables_json
    
    def to_dict(self) -> Dict:
        return {
            "chunk_text": self.chunk_text,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "chapter_path": self.chapter_path,
            "score": self.score,
            # 前端期望的字段别名
            "title": self.document_title,
            "text": self.chunk_text,
        }


class RetrievalService:
    """统一检索服务"""
    
    def __init__(self):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    def search(
        self,
        query: str,
        project_id: Optional[int] = None,
        file_types: Optional[List[str]] = None,
        chapter_prefix: Optional[str] = None,
        top_k: int = 5,
        expand_chunks: int = 1,
        token_limit: int = 4000
    ) -> List[RetrievedChunk]:
        """
        统一检索入口
        1. 对查询文本向量化
        2. 向量检索（多取一些用于后过滤）
        3. 内存中过滤 project_id / file_type
        4. 项目内文档优先
        5. 去重
        """
        # 向量化查询
        try:
            query_embedding = self.embedding_service.embed_query(query)
        except Exception as e:
            print(f"[RetrievalService] 向量化失败: {e}")
            return []
        
        # 多检索一些结果，用于后过滤
        fetch_k = max(top_k * 3, 15)
        all_chunks = []
        
        try:
            raw_results = self.vector_store.search(
                query_embedding,
                top_k=fetch_k,
                filters=None  # 不在向量层过滤，FAISS对复杂过滤支持有限
            )
            all_chunks = self._convert_results(raw_results)
        except Exception as e:
            print(f"[RetrievalService] 向量检索失败: {e}")
            all_chunks = []
        
        # 内存过滤：按project_id优先，按file_type过滤
        if project_id or file_types:
            project_chunks = []
            other_chunks = []
            
            # 获取项目内文档ID集合
            project_doc_ids = set()
            if project_id:
                try:
                    from app.core.database import SessionLocal
                    from app.models.document import Document
                    db = SessionLocal()
                    try:
                        project_doc_ids = set(
                            d.id for d in db.query(Document.id).filter(Document.project_id == project_id).all()
                        )
                    finally:
                        db.close()
                except Exception as e:
                    print(f"[RetrievalService] 查询项目文档失败: {e}")
            
            # 获取文档类型映射
            doc_type_map = {}
            if file_types:
                try:
                    from app.core.database import SessionLocal
                    from app.models.document import Document
                    db = SessionLocal()
                    try:
                        docs = db.query(Document).all()
                        doc_type_map = {d.id: d.file_type for d in docs}
                    finally:
                        db.close()
                except Exception:
                    pass
            
            for c in all_chunks:
                # file_type过滤
                if file_types:
                    dt = doc_type_map.get(c.document_id, "")
                    if dt and dt not in file_types:
                        continue
                
                # project_id优先级排序
                if project_doc_ids and c.document_id in project_doc_ids:
                    project_chunks.append(c)
                else:
                    other_chunks.append(c)
            
            all_chunks = project_chunks + other_chunks
        
        # 去重
        seen = set()
        merged = []
        for chunk in all_chunks:
            key = f"{chunk.document_id}:{chunk.chunk_text[:80]}"
            if key not in seen:
                seen.add(key)
                merged.append(chunk)
                if len(merged) >= top_k:
                    break
        
        return merged[:top_k]
    
    def assemble_context(
        self,
        chunks: List[RetrievedChunk],
        max_tokens: int = 4000
    ) -> str:
        """将检索结果组装为上下文文本"""
        context_parts = []
        total_length = 0
        
        for chunk in chunks:
            source_info = f"[来源: {chunk.document_title}"
            if chunk.page_number:
                source_info += f" 第{chunk.page_number}页"
            if chunk.section_title:
                source_info += f" {chunk.section_title}"
            source_info += "]"
            
            chunk_text = f"{source_info}\n{chunk.chunk_text}"
            estimated_tokens = len(chunk_text)
            
            if total_length + estimated_tokens > max_tokens * 2:  # 中文粗略估算
                break
            
            context_parts.append(chunk_text)
            total_length += estimated_tokens
        
        return "\n\n---\n\n".join(context_parts)
    
    def _convert_results(self, results: List[Dict]) -> List[RetrievedChunk]:
        """将向量库结果转换为RetrievedChunk列表，从DB取完整文本"""
        chunks = []
        
        db = None
        try:
            from app.core.database import SessionLocal
            from app.models.document import Document, Chunk as DBChunk
            db = SessionLocal()
            
            for result in results:
                metadata = result.get("metadata", {})
                document_id = metadata.get("document_id", 0)
                chunk_id = metadata.get("chunk_id")
                
                chunk_text = metadata.get("text", "")
                page_number = metadata.get("page_number")
                section_title = metadata.get("section_title", "")
                chapter_path = metadata.get("chapter_path", "")
                
                # 如果有chunk_id，从DB取完整文本
                if chunk_id:
                    db_chunk = db.query(DBChunk).filter(DBChunk.id == chunk_id).first()
                    if db_chunk:
                        chunk_text = db_chunk.chunk_text
                        page_number = page_number or db_chunk.page_number
                        section_title = section_title or db_chunk.section_title
                        chapter_path = chapter_path or db_chunk.chapter_path
                
                # 获取文档标题
                doc_title = metadata.get("file_name", "")
                if document_id:
                    doc = db.query(Document).filter(Document.id == document_id).first()
                    if doc:
                        doc_title = doc.title
                
                chunk = RetrievedChunk(
                    chunk_text=chunk_text or "",
                    document_id=document_id,
                    document_title=doc_title,
                    page_number=page_number,
                    section_title=section_title,
                    chapter_path=chapter_path,
                    score=result.get("score", 0.0),
                )
                chunks.append(chunk)
        except Exception as e:
            print(f"[RetrievalService] 转换结果失败: {e}")
            # 降级：直接使用metadata中的数据
            for result in results:
                metadata = result.get("metadata", {})
                chunks.append(RetrievedChunk(
                    chunk_text=metadata.get("text", ""),
                    document_id=metadata.get("document_id", 0),
                    document_title=metadata.get("file_name", metadata.get("title", "")),
                    page_number=metadata.get("page_number"),
                    section_title=metadata.get("section_title", ""),
                    chapter_path=metadata.get("chapter_path", ""),
                    score=result.get("score", 0.0),
                ))
        finally:
            if db:
                db.close()
        
        return chunks


# 全局单例
retrieval_service = RetrievalService()
