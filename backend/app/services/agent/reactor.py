import asyncio
import json
import time
import uuid
from typing import AsyncGenerator, List, Dict, Optional, Any

from app.core.config import settings
from app.services.llm_service import llm_service
from app.services.agent.tools import tool_registry, ToolCallResult
from app.services.agent.memory.conversation_memory import ConversationMemory
from app.services.agent.prompts.system_prompts import AGENT_SYSTEM_PROMPT, SECURITY_REMINDER
from app.services.agent.schemas import AgentResult


class ReActEngine:
    """ReAct (Thought-Action-Observation) 推理引擎。

    负责驱动 LLM 与工具之间的多轮交互循环：
      Thought  -> LLM 思考是否需要调用工具
      Action   -> 执行工具调用
      Observation -> 将工具结果反馈给 LLM，继续推理
    直到 LLM 给出最终文本回答或达到最大步数限制。
    """

    def __init__(self):
        self.max_steps = settings.AGENT_MAX_STEPS
        self.temperature = settings.AGENT_TEMPERATURE
        self.max_tool_chars = settings.AGENT_MAX_TOOL_TOKENS * 4

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """构建系统提示词，包含当前已注册工具的描述列表。"""
        tools = tool_registry.list_tools()
        tool_descs: List[str] = []
        for t in tools:
            tool_descs.append(f"- {t.name}: {t.description}")
        tool_descs_text = "\n".join(tool_descs) if tool_descs else "（暂无可用工具）"
        return AGENT_SYSTEM_PROMPT.format(tool_descriptions=tool_descs_text) + "\n" + SECURITY_REMINDER

    @staticmethod
    async def _emit(queue: Optional[asyncio.Queue], event: str, data: Dict[str, Any]) -> None:
        """向事件队列发送一条 SSE 事件（队列为 None 时静默跳过）。"""
        if queue is not None:
            await queue.put({"event": event, "data": data})

    def _serialize_tool_result(self, result: Any) -> str:
        """将工具返回值序列化为 JSON 字符串，并在超长时截断。"""
        if isinstance(result, ToolCallResult):
            result_data = result.data if result.success else {"error": result.error}
        else:
            result_data = result

        result_str = json.dumps(result_data, ensure_ascii=False, default=str)
        if len(result_str) > self.max_tool_chars:
            result_str = result_str[:self.max_tool_chars] + "...[结果已截断]"
        return result_str

    # ------------------------------------------------------------------
    # 核心：非流式执行
    # ------------------------------------------------------------------

    async def arun(
        self,
        user_message: str,
        memory: ConversationMemory,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> AgentResult:
        """执行 ReAct 循环，返回最终 AgentResult。

        :param user_message: 用户本轮输入
        :param memory:      对话记忆实例（会被原地修改）
        :param event_queue: 可选的 asyncio.Queue，用于向外推送 SSE 事件
        """
        system_prompt = self._build_system_prompt()
        tools_schemas = tool_registry.get_all_schemas()

        tools_used: List[str] = []
        all_sources: List[Dict] = []
        start_time = time.time()

        # 将用户消息写入记忆
        memory.add_user_message(user_message)

        for step in range(self.max_steps):
            # 发送 thinking 事件
            await self._emit(event_queue, "thinking", {
                "step": step + 1,
                "thought": f"正在分析问题...（第{step + 1}步）",
            })

            # 组装消息列表（含 system prompt + 历史）
            messages = memory.get_messages(system_prompt)

            # 调用 LLM（带 function calling）
            try:
                response = await llm_service.chat_with_tools(
                    messages=messages,
                    tools=tools_schemas,
                    temperature=self.temperature,
                )
            except Exception as e:
                error_msg = f"AI调用出错：{str(e)}"
                await self._emit(event_queue, "error", {
                    "error": error_msg,
                    "step": step + 1,
                })
                return AgentResult(
                    content=error_msg,
                    steps=step + 1,
                    error=str(e),
                )

            # ---- 有工具调用 -> 执行 Action ----
            if response.tool_calls:
                for idx, tool_call in enumerate(response.tool_calls):
                    tool_name = tool_call.name
                    tool_args = tool_call.arguments
                    # 为每次工具调用生成唯一 id，避免多工具同轮冲突
                    tool_call_id = f"call_{step}_{idx}_{uuid.uuid4().hex[:8]}"

                    # 发送 tool_call 事件
                    await self._emit(event_queue, "tool_call", {
                        "tool": tool_name,
                        "arguments": tool_args,
                        "step": step + 1,
                    })

                    tool = tool_registry.get(tool_name)
                    if tool is None:
                        error_msg = f"工具 '{tool_name}' 不存在"
                        memory.add_tool_result(tool_name, tool_call_id,
                                               json.dumps({"error": error_msg}, ensure_ascii=False))
                        await self._emit(event_queue, "tool_result", {
                            "tool": tool_name,
                            "error": error_msg,
                            "duration_ms": 0,
                        })
                        continue

                    # 执行工具
                    tool_start = time.time()
                    try:
                        result = await tool.ainvoke(**tool_args)
                        duration_ms = int((time.time() - tool_start) * 1000)

                        tools_used.append(tool_name)

                        # 收集引用来源
                        if isinstance(result, ToolCallResult) and result.references:
                            all_sources.extend(result.references)

                        # 序列化并写入记忆
                        result_str = self._serialize_tool_result(result)
                        memory.add_tool_result(tool_name, tool_call_id, result_str)

                        # 发送 tool_result 事件
                        if isinstance(result, ToolCallResult):
                            result_data = result.data if result.success else {"error": result.error}
                            success = result.success
                        else:
                            result_data = result
                            success = True

                        await self._emit(event_queue, "tool_result", {
                            "tool": tool_name,
                            "result": result_data,
                            "duration_ms": duration_ms,
                            "success": success,
                        })

                    except Exception as e:
                        duration_ms = int((time.time() - tool_start) * 1000)
                        error_msg = f"工具执行失败：{str(e)}"
                        memory.add_tool_result(
                            tool_name,
                            tool_call_id,
                            json.dumps({"error": error_msg}, ensure_ascii=False),
                        )
                        await self._emit(event_queue, "tool_result", {
                            "tool": tool_name,
                            "error": error_msg,
                            "duration_ms": duration_ms,
                        })

                # 工具执行完毕，进入下一轮 Thought
                continue

            # ---- 无工具调用 -> 最终回答 ----
            final_content = response.content or ""
            memory.add_assistant_message(final_content)
            total_duration_ms = int((time.time() - start_time) * 1000)

            await self._emit(event_queue, "done", {
                "content": final_content,
                "steps": step + 1,
                "tools_used": tools_used,
                "sources": all_sources,
                "duration_ms": total_duration_ms,
                "usage": response.usage,
            })

            return AgentResult(
                content=final_content,
                steps=step + 1,
                sources=all_sources,
                usage=response.usage,
                tools_used=tools_used,
            )

        # ---- 超过最大步数 ----
        timeout_msg = (
            "抱歉，当前问题较为复杂，我在多次尝试后未能完成。"
            "建议您将问题简化后重试，或拆分问题逐一询问。"
        )
        memory.add_assistant_message(timeout_msg)
        total_duration_ms = int((time.time() - start_time) * 1000)

        await self._emit(event_queue, "done", {
            "content": timeout_msg,
            "steps": self.max_steps,
            "tools_used": tools_used,
            "sources": all_sources,
            "duration_ms": total_duration_ms,
        })

        return AgentResult(
            content=timeout_msg,
            steps=self.max_steps,
            sources=all_sources,
            tools_used=tools_used,
        )

    # ------------------------------------------------------------------
    # 核心：流式执行（SSE 事件生成器）
    # ------------------------------------------------------------------

    async def arun_stream(
        self,
        user_message: str,
        memory: ConversationMemory,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式执行 ReAct 循环，逐事件 yield SSE 字典。

        事件格式::

            {"event": "thinking"|"tool_call"|"tool_result"|"done"|"error",
             "data":  {...}}
        """
        queue: asyncio.Queue = asyncio.Queue()

        # 在后台任务中运行 arun，事件通过 queue 传出
        task = asyncio.create_task(self.arun(user_message, memory, queue))

        try:
            while True:
                # 短暂等待队列中的事件；超时后检查任务是否已结束
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield event
                except asyncio.TimeoutError:
                    if task.done():
                        break
                    continue

            # 任务结束后排空队列中可能残留的事件（避免竞态丢数据）
            while not queue.empty():
                yield queue.get_nowait()

            # 重新抛出任务中的异常（若有）
            exc = task.exception()
            if exc is not None:
                raise exc
        finally:
            # 确保任务被清理
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass


# 全局单例
react_engine = ReActEngine()
