from typing import Dict, Any, List, Optional
from .base import BaseTool, ToolCallResult, ToolParameter
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store
from app.core.config import settings

class StandardSearchTool(BaseTool):
    name = "standard_search"
    description = "水利规范检索工具，专门用于搜索水利水电工程相关的规范、标准、规程条文，包括GB、SL、DL等标准"
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="检索关键词或问题，例如'坝顶超高'、'防洪标准'、'堤防设计'等",
            required=True,
        ),
        ToolParameter(
            name="code_name",
            type="string",
            description="可选，规范名称或编号，例如'GB 50201-2014'、'SL 274-2020'，不填则搜索所有规范",
            required=False,
        ),
        ToolParameter(
            name="top_k",
            type="integer",
            description="返回的条文数量，默认5",
            required=False,
            default=5,
        ),
    ]
    
    async def ainvoke(self, query: str, code_name: Optional[str] = None, top_k: int = 5, **kwargs) -> ToolCallResult:
        try:
            query_vec = embedding_service.embed_query(query)
            if not query_vec:
                return ToolCallResult(success=False, error="向量化失败")
            
            # 构建过滤条件
            filters = None
            if code_name:
                filters = {"file_name": {"$contains": code_name}}  # 简单匹配，实际由search方法处理
            
            results = vector_store.search(query_vec, top_k=top_k * 2, filters=None)  # 多取一些后过滤
            
            contexts = []
            references = []
            for r in results:
                meta = r.get("metadata", {})
                score = r.get("score", 0)
                file_name = meta.get("file_name", "") or meta.get("code_name", "")
                
                # 如果指定了规范名，过滤
                if code_name and code_name.lower() not in file_name.lower():
                    continue
                
                # 获取文本内容（兼容不同字段名）
                text_content = meta.get("text", "") or meta.get("content", "")
                
                # mock模式下降低阈值
                min_score = 0.0 if settings.MOCK_MODE else 0.3
                if score < min_score:
                    # 如果有精确关键词匹配也保留
                    query_keywords = [kw for kw in query.replace("的", " ").replace("是", " ").split() if len(kw) > 1]
                    if not any(kw in text_content for kw in query_keywords):
                        continue
                
                contexts.append({
                    "file_name": file_name,
                    "page_number": meta.get("page_number") or meta.get("article"),
                    "text": text_content[:600],
                    "similarity": round(score, 3),
                    "code_number": meta.get("code_number", ""),
                    "category": meta.get("category", ""),
                })
                references.append({
                    "file_name": file_name,
                    "page_number": meta.get("page_number") or meta.get("article"),
                    "snippet": text_content[:200],
                })
                
                if len(contexts) >= top_k:
                    break
            
            return ToolCallResult(
                success=True,
                data={
                    "query": query,
                    "code_name": code_name,
                    "results": contexts,
                    "result_count": len(contexts),
                    "tip": "检索到相关规范条文，请根据条文内容回答" if contexts else "未检索到相关规范条文",
                },
                references=references,
            )
        except Exception as e:
            return ToolCallResult(success=False, error=str(e))
