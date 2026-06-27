from typing import Optional
from .base import BaseTool, ToolCallResult, ToolParameter
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store


class FloodPlanQueryTool(BaseTool):
    name = "flood_plan_query"
    description = "防汛预案查询工具，根据水位、降雨量、工程名称等查询匹配的防汛应急预案、调度规程和响应措施"
    parameters = [
        ToolParameter(name="query", type="string", description="查询内容描述，如'水位超汛限'、'超标准洪水'、'应急响应'等", required=True),
        ToolParameter(name="water_level", type="number", description="当前水位（m），可选", required=False),
        ToolParameter(name="scenario", type="string", description="场景类型，如'超汛限'、'超警戒'、'超保证'、'超标准洪水'等", required=False),
    ]

    async def ainvoke(self, query: str, water_level: Optional[float] = None, scenario: Optional[str] = None, **kwargs) -> ToolCallResult:
        try:
            search_query = query
            if scenario:
                search_query = f"{scenario} {query}"
            if water_level:
                search_query += f" 水位{water_level}m"

            query_vec = embedding_service.embed_query(search_query + " 防汛预案 调度规程 应急响应")
            results = vector_store.search(query_vec, top_k=8)

            plans = []
            references = []
            for r in results:
                meta = r.get("metadata", {})
                score = r.get("score", 0)
                if score < 0.25:
                    continue

                file_name = meta.get("file_name", "")
                plans.append({
                    "document": file_name,
                    "page_number": meta.get("page_number"),
                    "content": meta.get("text", "")[:500],
                    "similarity": round(score, 3),
                })
                references.append({
                    "file_name": file_name,
                    "page_number": meta.get("page_number"),
                    "snippet": meta.get("text", "")[:200],
                })

            # 内置响应级别提示
            response_guide = ""
            if scenario and "超标准" in scenario:
                response_guide = "⚠️ 超标准洪水属非常情况，应立即启动最高级别应急响应，通知下游群众转移"
            elif scenario and "保证" in scenario:
                response_guide = "水位超保证水位：启动Ⅰ级应急响应，防汛责任人到岗，准备抢险"
            elif scenario and "警戒" in scenario:
                response_guide = "水位超警戒水位：启动Ⅲ级或Ⅱ级应急响应，加强巡查"
            elif water_level:
                response_guide = "请根据实际水位对照预案中的分级响应条件确定响应级别"

            return ToolCallResult(
                success=True,
                data={
                    "query": query,
                    "scenario": scenario,
                    "water_level": water_level,
                    "plans": plans[:5],
                    "plan_count": len(plans[:5]),
                    "response_guide": response_guide,
                    "warning": "⚠️ AI提供的防汛预案查询结果仅供辅助参考，实际防汛调度和应急响应决策必须由防汛指挥部门和相关责任人做出",
                },
                references=references,
            )
        except Exception as e:
            return ToolCallResult(success=False, error=str(e))
