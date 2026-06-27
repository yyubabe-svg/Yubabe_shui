from typing import Optional
from .base import BaseTool, ToolCallResult, ToolParameter
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store


class CodeLookupTool(BaseTool):
    name = "code_lookup"
    description = "规范条文精确查找工具，根据规范编号（如'GB 50201-2014'）和条文号（如'3.0.1'）精确查找条文内容"
    parameters = [
        ToolParameter(name="code", type="string", description="规范编号，如'GB 50201-2014'、'SL 252-2017'", required=True),
        ToolParameter(name="article", type="string", description="条文号，如'3.0.1'、'5.1.2'", required=False),
    ]

    async def ainvoke(self, code: str, article: Optional[str] = None, **kwargs) -> ToolCallResult:
        try:
            # 先尝试直接检索规范相关内容
            query = code
            if article:
                query = f"{code} 第{article}条"

            query_vec = embedding_service.embed_query(query)
            results = vector_store.search(query_vec, top_k=10)

            filtered = []
            for r in results:
                meta = r.get("metadata", {})
                file_name = meta.get("file_name", "")
                text = meta.get("text", "")

                # 匹配规范名
                if code.lower().replace(" ", "") not in file_name.lower().replace(" ", ""):
                    # 也检查内容中是否包含
                    if code not in text:
                        continue

                # 如果指定了条文号，检查内容是否包含
                if article and article not in text:
                    continue

                score = r.get("score", 0)
                if score < 0.2:
                    continue

                filtered.append({
                    "file_name": file_name,
                    "page_number": meta.get("page_number"),
                    "text": text[:800],
                    "similarity": round(score, 3),
                })

            return ToolCallResult(
                success=True,
                data={
                    "code": code,
                    "article": article,
                    "results": filtered[:5],
                    "result_count": len(filtered[:5]),
                },
                references=[{
                    "file_name": r["file_name"],
                    "page_number": r["page_number"],
                    "snippet": r["text"][:200],
                } for r in filtered[:3]],
            )
        except Exception as e:
            return ToolCallResult(success=False, error=str(e))
