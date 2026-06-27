from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
import time

class ToolParameter(BaseModel):
    name: str
    type: str  # string, number, integer, boolean, object, array
    description: str
    required: bool = True
    enum: Optional[list] = None
    default: Any = None

class ToolCallResult:
    """工具调用结果"""
    def __init__(self, success: bool = True, data: Any = None, 
                 error: Optional[str] = None, references: Optional[List[Dict]] = None):
        self.success = success
        self.data = data
        self.error = error
        self.references = references or []
        self.execution_time: float = 0.0

class BaseTool(ABC):
    """工具基类"""
    name: str = ""
    description: str = ""
    parameters: List[ToolParameter] = []
    
    @abstractmethod
    async def ainvoke(self, **kwargs) -> ToolCallResult:
        """异步执行工具"""
        pass
    
    def invoke(self, **kwargs) -> ToolCallResult:
        """同步执行"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self.ainvoke(**kwargs)).result()
                    return result
        except RuntimeError:
            pass
        return asyncio.run(self.ainvoke(**kwargs))
    
    def get_schema(self) -> dict:
        """获取OpenAI Function Calling格式schema"""
        properties = {}
        required = []
        for p in self.parameters:
            prop = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            if p.default is not None:
                prop["default"] = p.default
            properties[p.name] = prop
            if p.required:
                required.append(p.name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
