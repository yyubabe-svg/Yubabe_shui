import json
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from typing import Optional, List
from sqlalchemy.orm import Session
from app.schemas.agent import (
    AgentChatRequest, AgentChatSyncResponse,
    SessionResponse, SessionListResponse, SessionDetailResponse,
    ToolListResponse, ToolInvokeRequest, ToolInvokeResponse,
    ToolSchema,
)
from app.services.agent.agent_service import agent_service
from app.services.agent.tools import tool_registry
from app.models.user_usage import UserUsage
from app.api.routes.usage import get_current_user
from app.core.database import get_db

router = APIRouter()


@router.post("/chat/sync", response_model=AgentChatSyncResponse, summary="同步对话")
async def chat_sync(
    request: AgentChatRequest,
    user: UserUsage = Depends(get_current_user),
):
    """Agent同步对话接口（兼容旧模式，等待完整回复）"""
    try:
        # 修复11：使用认证用户的name，而非请求体中的user_name
        result = await agent_service.chat(
            message=request.message,
            session_id=request.session_id,
            user_name=user.name,
        )
        return AgentChatSyncResponse(
            session_id=result["session_id"],
            message_id=0,
            content=result["content"],
            steps=result["steps"],
            tools_used=result.get("tools_used", []),
            sources=result.get("sources", []),
            usage=result.get("usage"),
            duration_ms=result["duration_ms"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", summary="流式对话（SSE）")
async def chat_stream(
    request: AgentChatRequest,
    user: UserUsage = Depends(get_current_user),
):
    """Agent流式对话接口（Server-Sent Events）"""
    # 修复11：使用认证用户的name
    async def event_generator():
        try:
            async for event in agent_service.chat_stream(
                message=request.message,
                session_id=request.session_id,
                user_name=user.name,
            ):
                event_type = event.get("event", "message")
                data = event.get("data", {})
                yield {
                    "event": event_type,
                    "data": json.dumps(data, ensure_ascii=False, default=str),
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@router.get("/sessions", response_model=SessionListResponse, summary="获取会话列表")
async def list_sessions(
    limit: int = 50,
    user: UserUsage = Depends(get_current_user),
):
    """修复11：需要认证，使用user.name获取会话列表"""
    sessions = agent_service.list_sessions(user_name=user.name, limit=limit)
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                title=s.title or "新对话",
                mode=s.mode or "agent",
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=s.message_count or 0,
                summary=s.summary or "",
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, summary="获取会话详情")
async def get_session(
    session_id: str,
    user: UserUsage = Depends(get_current_user),
):
    """需要认证，且验证会话归属"""
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    # 验证会话归属
    if session.user_name != user.name:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    messages = agent_service.get_session_messages(session_id)
    return SessionDetailResponse(
        id=session.id,
        title=session.title or "新对话",
        mode=session.mode or "agent",
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=session.message_count or 0,
        summary=session.summary or "",
        messages=messages,
    )


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: str,
    user: UserUsage = Depends(get_current_user),
):
    """需要认证，且验证会话归属"""
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_name != user.name:
        raise HTTPException(status_code=403, detail="无权删除此会话")
    success = agent_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "message": "会话已删除"}


@router.post("/sessions/{session_id}/messages", summary="向指定会话发消息（流式）")
async def send_to_session(
    session_id: str,
    request: AgentChatRequest,
    user: UserUsage = Depends(get_current_user),
):
    """向已有会话发送消息（流式SSE）- 需要认证且验证归属"""
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_name != user.name:
        raise HTTPException(status_code=403, detail="无权向此会话发送消息")
    # 使用model_copy避免修改不可变的Pydantic模型
    request = request.model_copy(update={"session_id": session_id})
    return await chat_stream(request, user=user)


@router.get("/tools", response_model=ToolListResponse, summary="获取可用工具列表")
async def list_tools(
    user: UserUsage = Depends(get_current_user),
):
    """修复11：需要认证"""
    schemas = agent_service.list_tools()
    tools = []
    for s in schemas:
        func = s.get("function", {})
        tools.append(ToolSchema(
            name=func.get("name", ""),
            description=func.get("description", ""),
            parameters=func.get("parameters", {}),
        ))
    return ToolListResponse(tools=tools, total=len(tools))


@router.post("/tools/{name}/invoke", response_model=ToolInvokeResponse, summary="直接调用工具（调试）")
async def invoke_tool(
    name: str,
    request: ToolInvokeRequest,
    user: UserUsage = Depends(get_current_user),
):
    """修复11：需要认证"""
    result = await agent_service.invoke_tool(name, request.arguments)
    return ToolInvokeResponse(
        tool=name,
        success=result.get("success", False),
        data=result.get("data"),
        error=result.get("error"),
        duration_ms=result.get("duration_ms", 0),
    )


@router.get("/logs", summary="Agent任务日志（简化版）")
async def get_logs(
    limit: int = 50,
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """需要认证，只返回当前用户的日志"""
    from app.models.agent import AgentTaskLog, ConversationSession
    # 通过session关联过滤当前用户的日志
    logs = db.query(AgentTaskLog).join(
        ConversationSession, AgentTaskLog.session_id == ConversationSession.id
    ).filter(
        ConversationSession.user_name == user.name
    ).order_by(AgentTaskLog.created_at.desc()).limit(limit).all()
    return {
        "logs": [
            {
                "id": l.id,
                "session_id": l.session_id,
                "task_type": l.task_type,
                "status": l.status,
                "steps_count": l.steps_count,
                "tools_used": l.tools_used,
                "duration_ms": l.duration_ms,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "total": len(logs),
    }
