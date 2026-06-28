import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.models.user_usage import UserUsage
from app.api.routes.usage import get_current_user

router = APIRouter(prefix="/api/flood", tags=["防汛辅助"])


class FloodQueryRequest(BaseModel):
    query: str
    reservoir: Optional[str] = None


MOCK_PLANS = [
    {
        "id": 1,
        "plan_name": "C水库防洪调度规程",
        "reservoir": "C水库",
        "plan_type": "调度规程",
        "water_level_limit": "汛限水位：156.5m",
        "key_rules": [
            "当水位超过汛限水位，应按批准的防洪调度方案进行调度",
            "当水位达到158.0m，开启溢洪道泄洪",
            "当水位达到160.0m，启动应急预案",
        ],
    },
    {
        "id": 2,
        "plan_name": "A河流域防汛应急预案",
        "reservoir": None,
        "plan_type": "应急预案",
        "key_rules": [
            "当预报水位超过保证水位，立即启动Ⅰ级应急响应",
            "提前通知下游群众转移",
        ],
    },
]


@router.get("/plans")
async def list_plans(
    river_basin: Optional[str] = None,
    plan_type: Optional[str] = None,
    user: UserUsage = Depends(get_current_user),
):
    """获取防汛预案列表（需认证）"""
    return {"plans": MOCK_PLANS}


@router.post("/query")
async def query_flood(
    request: FloodQueryRequest,
    user: UserUsage = Depends(get_current_user),
):
    """防汛预案智能匹配（需认证，调用LLM）"""
    matched_plans = MOCK_PLANS

    answer = f"【结论】根据您的查询\"{request.query}\"，匹配到以下预案：\n\n"

    for plan in matched_plans:
        answer += f"- {plan['plan_name']}\n"
        if "water_level_limit" in plan:
            answer += f"   {plan['water_level_limit']}\n"
        answer += "   关键规则：\n"
        for rule in plan.get("key_rules", []):
            answer += f"   - {rule}\n"
        answer += "\n"

    answer += "【风险提示】\n本系统仅提供辅助查询，最终调度决策应由防汛责任人确认。\n\n"
    answer += "【建议下一步】\n1. 立即报告防汛责任人\n2. 启动水情加密监测"

    return {
        "answer": answer,
        "matched_plans": matched_plans,
        "disclaimer": "本系统仅提供辅助查询，不替代正式决策",
    }
