from typing import Dict, List, Optional
from .base import BaseMemory


class ConversationMemory(BaseMemory):
    def __init__(self, max_messages: int = 30):
        self._messages: List[Dict] = []
        self._summary: str = ""
        self.max_messages = max_messages

    def add_user_message(self, content: str):
        self._messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant_message(self, content: str, tool_calls: Optional[List] = None):
        msg = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._messages.append(msg)
        self._trim()

    def add_tool_result(self, tool_name: str, tool_call_id: str, content: str):
        self._messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id or "call_0",
            "name": tool_name,
            "content": str(content)[:2000]
        })

    def add_thought(self, thought: str):
        self._messages.append({"role": "assistant", "content": thought, "is_thought": True})

    def get_messages(self, system_prompt: str) -> List[Dict]:
        messages = [{"role": "system", "content": system_prompt}]
        if self._summary:
            messages.append({
                "role": "system",
                "content": f"之前对话的摘要：\n{self._summary}"
            })
        # 过滤掉is_thought标记的消息（内部思考不发送给LLM）
        for msg in self._messages:
            if not msg.get("is_thought"):
                clean_msg = {k: v for k, v in msg.items() if k != "is_thought"}
                messages.append(clean_msg)
        return messages

    def _trim(self):
        """简单的消息裁剪：保留最近max_messages条"""
        if len(self._messages) > self.max_messages:
            # 保留系统相关消息和最近的消息
            self._messages = self._messages[-self.max_messages:]

    def clear(self):
        self._messages = []
        self._summary = ""

    @property
    def message_count(self) -> int:
        return len([m for m in self._messages if m["role"] in ("user", "assistant")])
