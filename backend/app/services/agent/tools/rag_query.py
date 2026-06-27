from typing import Dict, Any, List, Optional
from .base import BaseTool, ToolCallResult, ToolParameter
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store

class RAGQueryTool(BaseTool):
    name = "rag_query"
    description = "基础知识库检索工具，当其他专业工具不匹配时使用，可以搜索知识库中的所有文档内容来回答问题"
    parameters = [
        ToolParameter(
            name="question",
            type="string",
            description="用户的问题",
            required=True,
        ),
        ToolParameter(
            name="top_k",
            type="integer",
            description="返回的最相关文档片段数量，默认5",
            required=False,
            default=5,
        ),
    ]
    
    async def ainvoke(self, question: str, top_k: int = 5, **kwargs) -> ToolCallResult:
        try:
            # 向量化查询
            query_vec = embedding_service.embed_query(question)
            if not query_vec:
                return ToolCallResult(success=False, error="向量化失败")
            
            # 向量检索
            results = vector_store.search(query_vec, top_k=top_k)
            
            # 格式化结果
            contexts = []
            references = []
            for r in results:
                meta = r.get("metadata", {})
                score = r.get("score", 0)
                if score < 0.3:  # 相似度阈值
                    continue
                context_item = {
                    "file_name": meta.get("file_name", "未知文件"),
                    "page_number": meta.get("page_number", "未知页码"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "text": meta.get("text", "")[:500],
                    "similarity": round(score, 3),
                }
                contexts.append(context_item)
                references.append({
                    "file_name": meta.get("file_name", "未知文件"),
                    "page_number": meta.get("page_number"),
                    "snippet": meta.get("text", "")[:200],
                })
            
            return ToolCallResult(
                success=True,
                data={
                    "question": question,
                    "results": contexts,
                    "result_count": len(contexts),
                },
                references=references,
            )
        except Exception as e:
            return ToolCallResult(success=False, error=str(e))
