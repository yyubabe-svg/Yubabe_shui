import uuid
import time
import json
from datetime import datetime
from typing import Optional, List, Dict, AsyncGenerator, Any
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.agent import ConversationSession, ConversationMessage, AgentTaskLog
from app.services.agent.reactor import react_engine
from app.services.agent.memory.conversation_memory import ConversationMemory


class AgentService:
    def __init__(self):
        pass

    def _get_db(self) -> Session:
        return SessionLocal()

    def create_session(self, user_name: str = "default_user", title: Optional[str] = None) -> ConversationSession:
        db = self._get_db()
        try:
            session_id = str(uuid.uuid4())
            session = ConversationSession(
                id=session_id,
                user_name=user_name,
                title=title or "新对话",
                mode="agent",
                message_count=0,
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        db = self._get_db()
        try:
            return db.query(ConversationSession).filter(ConversationSession.id == session_id).first()
        finally:
            db.close()

    def list_sessions(self, user_name: str = "default_user", limit: int = 50) -> List[ConversationSession]:
        db = self._get_db()
        try:
            sessions = db.query(ConversationSession)\
                .filter(ConversationSession.user_name == user_name)\
                .order_by(ConversationSession.updated_at.desc())\
                .limit(limit)\
                .all()
            return sessions
        finally:
            db.close()

    def delete_session(self, session_id: str) -> bool:
        db = self._get_db()
        try:
            session = db.query(ConversationSession).filter(ConversationSession.id == session_id).first()
            if session:
                db.delete(session)
                db.commit()
                return True
            return False
        finally:
            db.close()

    def get_session_messages(self, session_id: str) -> List[Dict]:
        db = self._get_db()
        try:
            messages = db.query(ConversationMessage)\
                .filter(ConversationMessage.session_id == session_id)\
                .order_by(ConversationMessage.created_at.asc())\
                .all()
            result = []
            for msg in messages:
                item = {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
                if msg.tool_calls:
                    item["tool_calls"] = msg.tool_calls
                result.append(item)
            return result
        finally:
            db.close()

    def _save_message(self, session_id: str, role: str, content: str, tool_calls: List = None, token_usage: Dict = None, step: int = 0):
        db = self._get_db()
        try:
            msg = ConversationMessage(
                session_id=session_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                token_usage=token_usage,
                step=step,
            )
            db.add(msg)

            # 更新session
            session = db.query(ConversationSession).filter(ConversationSession.id == session_id).first()
            if session:
                session.message_count = (session.message_count or 0) + 1
                session.updated_at = datetime.utcnow()
                # 自动设置标题（第一条用户消息的前20字）
                if role == "user" and (not session.title or session.title == "新对话"):
                    session.title = content[:20] + ("..." if len(content) > 20 else "")

            db.commit()
            db.refresh(msg)
            return msg.id
        finally:
            db.close()

    async def chat(self, message: str, session_id: Optional[str] = None, user_name: str = "default_user") -> Dict:
        """同步对话"""
        # 获取或创建session
        if session_id:
            session = self.get_session(session_id)
            if not session:
                session = self.create_session(user_name)
                session_id = session.id
        else:
            session = self.create_session(user_name)
            session_id = session.id

        # 保存用户消息
        self._save_message(session_id, "user", message)

        # 创建记忆并加载历史
        memory = ConversationMemory()
        # 加载最近的历史消息到记忆
        history = self.get_session_messages(session_id)
        for msg in history[:-1]:  # 排除刚保存的用户消息（会在arun中添加）
            if msg["role"] == "user":
                memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                memory.add_assistant_message(msg["content"], msg.get("tool_calls"))

        start_time = time.time()

        try:
            result = await react_engine.arun(message, memory)

            duration_ms = int((time.time() - start_time) * 1000)

            # 保存AI回复
            self._save_message(
                session_id, "assistant", result.content,
                tool_calls=[{"name": t} for t in result.tools_used] if result.tools_used else None,
                token_usage=result.usage,
            )

            # 记录任务日志
            self._save_task_log(session_id, "chat", message[:100], result.tools_used, result.steps, duration_ms, "success" if not result.error else "failed", result.error)

            return {
                "session_id": session_id,
                "content": result.content,
                "steps": result.steps,
                "tools_used": result.tools_used,
                "sources": result.sources,
                "usage": result.usage,
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._save_task_log(session_id, "chat", message[:100], [], 0, duration_ms, "failed", str(e))
            raise

    async def chat_stream(self, message: str, session_id: Optional[str] = None, user_name: str = "default_user") -> AsyncGenerator[Dict[str, Any], None]:
        """流式对话，yield SSE事件字典"""
        # 获取或创建session
        if session_id:
            session = self.get_session(session_id)
            if not session:
                session = self.create_session(user_name)
                session_id = session.id
        else:
            session = self.create_session(user_name)
            session_id = session.id

        # 发送metadata事件
        yield {"event": "metadata", "data": {"session_id": session_id}}

        # 保存用户消息
        self._save_message(session_id, "user", message)

        # 创建记忆
        memory = ConversationMemory()
        history = self.get_session_messages(session_id)
        for msg in history[:-1]:
            if msg["role"] == "user":
                memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                memory.add_assistant_message(msg["content"], msg.get("tool_calls"))

        start_time = time.time()
        final_content = ""
        final_tools = []
        final_sources = []
        steps = 0
        error_msg = None

        try:
            import asyncio
            queue: asyncio.Queue = asyncio.Queue()

            # 启动ReAct任务
            task = asyncio.create_task(react_engine.arun(message, memory, queue))

            while not task.done() or not queue.empty():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    event_type = event.get("event", "")
                    data = event.get("data", {})

                    if event_type == "done":
                        final_content = data.get("content", "")
                        final_tools = data.get("tools_used", [])
                        final_sources = data.get("sources", [])
                        steps = data.get("steps", 0)
                    elif event_type == "error":
                        error_msg = data.get("error", "未知错误")

                    yield event
                except asyncio.TimeoutError:
                    if task.done():
                        # 排空队列
                        while not queue.empty():
                            event = queue.get_nowait()
                            yield event
                        break
                    continue

            # 等待任务完成
            await task

        except Exception as e:
            error_msg = str(e)
            yield {"event": "error", "data": {"error": str(e)}}

        duration_ms = int((time.time() - start_time) * 1000)

        # 保存最终回复
        if final_content:
            self._save_message(
                session_id, "assistant", final_content,
                tool_calls=[{"name": t} for t in final_tools] if final_tools else None,
            )

        self._save_task_log(
            session_id, "chat_stream", message[:100],
            final_tools, steps, duration_ms,
            "success" if not error_msg else "failed", error_msg
        )

    def _save_task_log(self, session_id: str, task_type: str, input_summary: str, tools_used: List, steps: int, duration_ms: int, status: str, error_msg: str = None):
        db = self._get_db()
        try:
            log = AgentTaskLog(
                session_id=session_id,
                task_type=task_type,
                input_summary=input_summary,
                tools_used=tools_used,
                steps_count=steps,
                duration_ms=duration_ms,
                status=status,
                error_msg=error_msg,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()

    def list_tools(self) -> List[Dict]:
        from app.services.agent.tools import tool_registry
        return tool_registry.get_all_schemas()

    async def invoke_tool(self, tool_name: str, arguments: Dict) -> Dict:
        from app.services.agent.tools import tool_registry
        tool = tool_registry.get(tool_name)
        if not tool:
            return {"success": False, "error": f"工具 '{tool_name}' 不存在"}

        start_time = time.time()
        try:
            result = await tool.ainvoke(**arguments)
            duration_ms = int((time.time() - start_time) * 1000)

            from app.services.agent.tools.base import ToolCallResult
            if isinstance(result, ToolCallResult):
                return {
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "duration_ms": duration_ms,
                }
            return {
                "success": True,
                "data": result,
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {"success": False, "error": str(e), "duration_ms": duration_ms}


agent_service = AgentService()
