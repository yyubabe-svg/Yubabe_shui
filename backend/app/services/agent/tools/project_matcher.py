from typing import Dict, Any, Optional
from .base import BaseTool, ToolCallResult, ToolParameter
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store


class ProjectMatcherTool(BaseTool):
    name = "project_matcher"
    description = "工程案例匹配工具，根据工程类型和关键参数（如坝高、库容、防洪标准）检索相似的历史工程案例供参考"
    parameters = [
        ToolParameter(name="project_type", type="string", description="工程类型，如'水库除险加固'、'堤防工程'、'河道治理'、'水电站'等", required=True),
        ToolParameter(name="parameters", type="object", description="工程参数字典，可包含：坝高(m)、库容(万m3)、防洪标准(年一遇)、工程等别等", required=False, default={}),
        ToolParameter(name="top_k", type="integer", description="返回案例数量，默认3", required=False, default=3),
    ]

    async def ainvoke(self, project_type: str, parameters: Optional[Dict[str, Any]] = None, top_k: int = 3, **kwargs) -> ToolCallResult:
        try:
            params = parameters or {}
            # 构建查询
            query_parts = [project_type]
            for k, v in params.items():
                query_parts.append(f"{k}{v}")
            query = " ".join(query_parts) + " 工程案例 设计"

            query_vec = embedding_service.embed_query(query)
            results = vector_store.search(query_vec, top_k=top_k * 3)

            cases = []
            references = []
            for r in results:
                meta = r.get("metadata", {})
                score = r.get("score", 0)
                if score < 0.3:
                    continue

                file_name = meta.get("file_name", "")
                cases.append({
                    "project_name": file_name.replace(".pdf", "").replace(".docx", "").replace(".txt", ""),
                    "file_name": file_name,
                    "page_number": meta.get("page_number"),
                    "summary": meta.get("text", "")[:400],
                    "similarity": round(score, 3),
                })
                references.append({
                    "file_name": file_name,
                    "page_number": meta.get("page_number"),
                    "snippet": meta.get("text", "")[:200],
                })
                if len(cases) >= top_k:
                    break

            return ToolCallResult(
                success=True,
                data={
                    "project_type": project_type,
                    "parameters": params,
                    "cases": cases,
                    "case_count": len(cases),
                    "tip": "以下为相似历史工程案例，仅供参考，具体设计应结合本工程实际情况" if cases else "未检索到足够相似的工程案例",
                },
                references=references,
            )
        except Exception as e:
            return ToolCallResult(success=False, error=str(e))
