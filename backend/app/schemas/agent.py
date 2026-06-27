from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID，不传则新建会话")
    user_name: str = Field("default_user", description="用户名")


class AgentChatSyncResponse(BaseModel):
    session_id: str
    message_id: int
    content: str
    steps: int
    tools_used: List[str] = []
    sources: List[Dict] = []
    usage: Optional[Dict] = None
    duration_ms: int


class SessionResponse(BaseModel):
    id: str
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    summary: Optional[str] = ""


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int


class SessionDetailResponse(SessionResponse):
    messages: List[Dict[str, Any]]


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolListResponse(BaseModel):
    tools: List[ToolSchema]
    total: int


class ToolInvokeRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolInvokeResponse(BaseModel):
    tool: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: int
