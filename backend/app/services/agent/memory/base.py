from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseMemory(ABC):
    @abstractmethod
    def add_user_message(self, content: str):
        pass

    @abstractmethod
    def add_assistant_message(self, content: str, tool_calls: Optional[List] = None):
        pass

    @abstractmethod
    def add_tool_result(self, tool_name: str, tool_call_id: str, content: str):
        pass

    @abstractmethod
    def get_messages(self, system_prompt: str) -> List[Dict]:
        pass

    @abstractmethod
    def clear(self):
        pass
