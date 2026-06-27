from typing import Dict, List, Optional
from .base import BaseMemory

class LongTermMemory(BaseMemory):
    """长期记忆（简化版本，后续迭代完善）"""
    
    def __init__(self, user_name: str = "default_user"):
        self.user_name = user_name
        self._preferences: Dict[str, Any] = {}
        self._history_summaries: List[Dict] = []
    
    def add_user_message(self, content: str):
        pass
    
    def add_assistant_message(self, content: str, tool_calls: Optional[List] = None):
        pass
    
    def add_tool_result(self, tool_name: str, tool_call_id: str, content: str):
        pass
    
    def get_messages(self, system_prompt: str) -> List[Dict]:
        return []
    
    def clear(self):
        self._preferences = {}
        self._history_summaries = []
