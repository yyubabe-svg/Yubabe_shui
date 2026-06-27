from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class AgentStatus(str, Enum):
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    RESPONDING = "responding"
    DONE = "done"
    ERROR = "error"


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class AgentResponse:
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    thought: str = ""
    usage: Optional[Dict[str, int]] = None
    finish_reason: str = "stop"


@dataclass
class AgentResult:
    content: str
    steps: int
    sources: List[Dict] = field(default_factory=list)
    usage: Optional[Dict[str, int]] = None
    tools_used: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SSEEvent:
    event: str  # metadata, thinking, tool_call, tool_result, token, done, error
    data: Dict[str, Any]
