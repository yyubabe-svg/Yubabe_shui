import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from typing import Optional, List
from app.schemas.agent import (
    AgentChatRequest, AgentChatSyncResponse,
    SessionResponse, SessionListResponse, SessionDetailResponse,
    ToolListResponse, ToolInvokeRequest, ToolInvokeResponse,
    ToolSchema,
)
from app.services.agent.agent_service import agent_service
from app.services.agent.tools import tool_registry

router = APIRouter()


@router.post("/chat/sync", response_model=AgentChatSyncResponse, summary="同步对话")
async def chat_sync(request: AgentChatRequest):
    """Agent同步对话接口（兼容旧模式，等待完整回复）"""
    try:
        result = await agent_service.chat(
            message=request.message,
            session_id=request.session_id,
            user_name=request.user_name,
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
async def chat_stream(request: AgentChatRequest):
    """Agent流式对话接口（Server-Sent Events）"""
    async def event_generator():
        try:
            async for event in agent_service.chat_stream(
                message=request.message,
                session_id=request.session_id,
                user_name=request.user_name,
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
async def list_sessions(user_name: str = "default_user", limit: int = 50):
    sessions = agent_service.list_sessions(user_name=user_name, limit=limit)
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
async def get_session(session_id: str):
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
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
async def delete_session(session_id: str):
    success = agent_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "message": "会话已删除"}


@router.post("/sessions/{session_id}/messages", summary="向指定会话发消息（流式）")
async def send_to_session(session_id: str, request: AgentChatRequest):
    """向已有会话发送消息（流式SSE）"""
    request.session_id = session_id
    return await chat_stream(request)


@router.get("/tools", response_model=ToolListResponse, summary="获取可用工具列表")
async def list_tools():
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
async def invoke_tool(name: str, request: ToolInvokeRequest):
    result = await agent_service.invoke_tool(name, request.arguments)
    return ToolInvokeResponse(
        tool=name,
        success=result.get("success", False),
        data=result.get("data"),
        error=result.get("error"),
        duration_ms=result.get("duration_ms", 0),
    )


@router.get("/logs", summary="Agent任务日志（简化版）")
async def get_logs(limit: int = 50):
    from app.core.database import SessionLocal
    from app.models.agent import AgentTaskLog
    db = SessionLocal()
    try:
        logs = db.query(AgentTaskLog).order_by(AgentTaskLog.created_at.desc()).limit(limit).all()
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
    finally:
        db.close()
