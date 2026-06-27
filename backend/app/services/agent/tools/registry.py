from typing import Dict, List, Optional
from .base import BaseTool

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())
    
    def get_all_schemas(self) -> List[dict]:
        return [t.get_schema() for t in self._tools.values()]

tool_registry = ToolRegistry()
