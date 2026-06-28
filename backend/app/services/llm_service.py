import httpx
import json
import asyncio
import re
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from app.core.config import settings


RAG_PROMPT_TEMPLATE = """你是"蜀水智库 AI"，一个服务于水利勘测设计院的专业知识库助手。

你必须遵守以下规则：
1. 只能基于系统提供的资料回答；
2. 不得编造规范、条文、数值、项目经历；
3. 如果资料不足，请明确说明"当前知识库资料不足，无法确定"；
4. 每个重要结论必须附带引用来源；
5. 回答要专业、简洁、结构化；
6. 涉及防汛调度时，只能提供辅助查询和预案匹配，不能替代正式决策；
7. 涉及合规审查时，只能给出初审意见，最终结论应由专业人员复核。

用户问题：{question}

参考资料：
{context}

请根据以上资料回答用户问题。如果资料不足，请明确说明。

输出格式：
【结论】
……

【依据】
1. 文件：……
   页码：……
   原文片段：……

【风险提示】
……

【建议下一步】
……
"""

REVIEW_PROMPT_TEMPLATE = """你是水利工程设计文件合规初审助手。

请根据用户上传的设计说明书内容和知识库中的规范依据，完成初步审查。

任务：
1. 提取工程名称、工程类型、坝高、库容、工程等级、防洪标准、设计暴雨重现期等关键参数；
2. 判断是否缺少关键参数；
3. 根据知识库规范进行初步比对；
4. 输出疑似风险；
5. 给出修改建议；
6. 每条建议必须引用规范依据；
7. 如果资料不足，请说明无法确定。

设计说明书内容：
{document_content}

参考资料：
{context}

输出格式：
【一、参数识别表】
| 参数 | 识别结果 | 原文位置 |

【二、初审结论】
……

【三、疑似风险】
……

【四、缺失信息】
……

【五、修改建议】
……

【六、规范依据】
……
"""


@dataclass
class ToolCall:
    """工具调用"""
    name: str
    arguments: Dict[str, Any]


@dataclass
class ChatResponse:
    """聊天响应（含工具调用）"""
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "tool_calls": [
                {"name": tc.name, "arguments": tc.arguments}
                for tc in self.tool_calls
            ],
            "usage": self.usage,
        }


class LLMService:
    """LLM 服务，支持多种 Provider"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.mock_mode = settings.MOCK_MODE
    
    # ------------------------------------------------------------------
    # 原有公开接口（保持向后兼容）
    # ------------------------------------------------------------------
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """生成文本（兼容旧接口）"""
        if self.mock_mode or self.provider == "mock":
            return self._mock_generate(prompt)
        
        if self.provider in ("openai", "volcano"):
            try:
                return await self._generate_completions(prompt, system_prompt)
            except Exception as e:
                # 修复4：非mock模式下打印详细错误并返回明确错误消息，不返回假答案
                import traceback
                print(f"[LLM] generate 调用失败 (provider={self.provider}): {e}")
                traceback.print_exc()
                return "AI服务暂时不可用，请稍后重试。"
        else:
            # 修复4：未知provider不再静默mock，返回错误提示
            print(f"[LLM] 未知的 LLM_PROVIDER: {self.provider}")
            return "AI服务配置错误，请联系管理员。"
    
    async def rag_query(self, question: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """RAG 问答"""
        context = self._format_context(retrieved_chunks)
        # 修复4：str.format()在用户输入含花括号时会报错，改用字符串替换（使用安全占位符）
        prompt = RAG_PROMPT_TEMPLATE.replace("{question}", question).replace("{context}", context)
        return await self.generate(prompt)
    
    async def review_document(self, document_content: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """合规审查"""
        context = self._format_context(retrieved_chunks)
        # 修复4：str.format()在用户输入含花括号时会报错，改用字符串替换
        prompt = REVIEW_PROMPT_TEMPLATE.replace("{document_content}", document_content).replace("{context}", context)
        return await self.generate(prompt)
    
    # ------------------------------------------------------------------
    # 新增公开接口
    # ------------------------------------------------------------------
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        非流式聊天，接受 OpenAI 格式消息列表。
        
        :param messages: [{"role": "user/assistant/system", "content": "..."}]
        :return: 模型返回的文本内容
        """
        if self.mock_mode or self.provider == "mock":
            # 从 messages 中提取最后一条用户消息用于 mock
            last_user_msg = self._extract_last_user_content(messages)
            return self._mock_generate(last_user_msg)
        
        try:
            return await self._chat_api(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
        except Exception as e:
            # 修复4：非mock模式下不再静默fallback到假答案，而是打印详细错误并返回明确错误消息
            import traceback
            print(f"[LLM] chat API 调用失败 (provider={self.provider}): {e}")
            traceback.print_exc()
            if self.mock_mode or self.provider == "mock":
                last_user_msg = self._extract_last_user_content(messages)
                return self._mock_generate(last_user_msg)
            return "AI服务暂时不可用，请稍后重试。"
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天（异步生成器），逐 token yield 字符串内容。
        
        支持 SSE 格式解析（data: {...}\\n\\n）。
        """
        if self.mock_mode or self.provider == "mock":
            last_user_msg = self._extract_last_user_content(messages)
            mock_text = self._mock_generate(last_user_msg)
            # 逐字 yield，带小延迟，模拟打字效果
            for ch in mock_text:
                yield ch
                await asyncio.sleep(0.01)
            return
        
        try:
            async for chunk in self._chat_api_stream(
                messages=messages,
                tools=tools,
                temperature=temperature,
            ):
                yield chunk
        except Exception as e:
            # 修复4：流式中断时yield错误提示，而不是继续yield mock假文本
            import traceback
            print(f"[LLM] chat_stream API 调用失败 (provider={self.provider}): {e}")
            traceback.print_exc()
            if self.mock_mode or self.provider == "mock":
                last_user_msg = self._extract_last_user_content(messages)
                mock_text = self._mock_generate(last_user_msg)
                for ch in mock_text:
                    yield ch
                    await asyncio.sleep(0.01)
            else:
                yield "\n\n[错误] AI服务暂时不可用，请稍后重试。"
    
    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> ChatResponse:
        """
        带 Function Calling 的聊天。
        
        :return: ChatResponse(content, tool_calls, usage)
        """
        if self.mock_mode or self.provider == "mock":
            return await self._mock_chat_with_tools(messages, tools)
        
        try:
            return await self._chat_api_with_tools(
                messages=messages,
                tools=tools,
                temperature=temperature,
            )
        except Exception as e:
            # 修复4：非mock模式下不再静默fallback到假数据，打印详细错误并向上传播或返回错误
            import traceback
            print(f"[LLM] chat_with_tools API 调用失败 (provider={self.provider}): {e}")
            traceback.print_exc()
            if self.mock_mode or self.provider == "mock":
                return await self._mock_chat_with_tools(messages, tools)
            # 非mock模式：抛出异常让上层（如reactor）处理错误
            raise
    
    # ------------------------------------------------------------------
    # Mock 逻辑
    # ------------------------------------------------------------------
    
    def _mock_generate(self, prompt: str) -> str:
        """Mock 模式：根据 prompt 内容返回预设回答"""
        if "小型水库除险加固" in prompt or "规范" in prompt:
            return self._mock_standard_answer()
        
        if "防洪排涝规划" in prompt or "历史项目" in prompt or "对比" in prompt:
            return self._mock_project_answer()
        
        if "汛限水位" in prompt or "预案" in prompt or "调度" in prompt:
            return self._mock_flood_answer()
        
        if "参数识别" in prompt or "设计说明书" in prompt or "坝高" in prompt:
            return self._mock_review_answer()
        
        # 检测是否是ISO信息提取请求
        if "project_name" in prompt or "项目编码" in prompt or "质量控制分级" in prompt:
            return self._mock_iso_extract()
        
        return self._mock_default_answer()
    
    def _mock_iso_extract(self) -> str:
        """Mock ISO信息提取"""
        return json.dumps({
            "project_name": "某河道综合治理工程",
            "project_code": "CDSD260099X",
            "feature_code": "X",
            "design_stage": "初步设计",
            "report_date": "2026年6月",
            "client": "某某区水务局",
            "work_scope": "综合治理河长3.2km，新建堤防2.8km，河道清淤3.2km，新建穿堤建筑物2座。",
            "engineering_overview": "本工程为河道综合治理工程，工程等别为Ⅴ等，主要建筑物级别为5级，防洪标准为20年一遇，排涝标准为10年一遇。",
            "design_basis": "《防洪标准》GB 50201-2014、《水利水电工程等级划分及洪水标准》SL 252-2017、《堤防工程设计规范》GB 50286-2013等",
            "technical_points": "堤线布置、堤身结构设计、岸坡防护、清淤疏浚设计",
            "risk_points": "1、工程区地质条件需进一步查明；2、施工期防汛风险；3、水土流失防治",
            "customer_requirements": "满足20年一遇防洪标准，堤顶高程满足防洪要求",
            "external_resources": "需进行工程地质勘察",
            "project_grade": "Ⅴ等",
            "building_level": "5级",
            "flood_standard": "20年一遇",
            "drainage_standard": "10年一遇",
            "involved_majors": ["工程测量", "工程地质", "水文", "规划/节水", "水工建筑物", "土建/管理/安全", "施工/节能", "环境保护", "水土保持", "造价"],
            "applicable_codes": [
                {"name": "防洪标准", "code": "GB 50201-2014"},
                {"name": "水利水电工程等级划分及洪水标准", "code": "SL 252-2017"},
                {"name": "堤防工程设计规范", "code": "GB 50286-2013"},
                {"name": "水利水电工程初步设计报告编制规程", "code": "SL/T 619-2021"},
                {"name": "水工建筑物抗震设计规范", "code": "SL 203-97"},
                {"name": "水利水电工程边坡设计规范", "code": "SL 386-2007"}
            ]
        }, ensure_ascii=False)
    
    def _mock_standard_answer(self) -> str:
        return """【结论】
小型水库除险加固设计需要重点参考以下规范：

1. 《水库大坝安全鉴定办法》（水建管〔2003〕271号）
2. 《水利水电工程等级划分及洪水标准》（SL 252-2017）
3. 《碾压式土石坝设计规范》（SL 274-2020）
4. 《溢洪道设计规范》（SL 253-2018）
5. 《水工建筑物抗震设计规范》（SL 203-2013）

【依据】
1. 文件：《水利水电工程等级划分及洪水标准》SL 252-2017
   页码：第12页
   原文片段："小型水库（总库容10万~1000万m³）的工程等别为Ⅳ等或Ⅴ等，主要建筑物级别为4级或5级。"

【风险提示】
- 不同省份可能有地方补充规定，需结合当地水利厅要求
- 除险加固设计前必须完成大坝安全鉴定

【建议下一步】
1. 确认该水库已完成大坝安全鉴定
2. 收集流域最新水文资料"""
    
    def _mock_project_answer(self) -> str:
        return """【结论】
近十年该流域防洪排涝规划相关项目如下：

| 项目名称 | 年份 | 流域 | 设计暴雨重现期 | 防洪标准 |
|---------|------|------|--------------|---------|
| A河流域防洪规划修编 | 2018 | A河 | 50年一遇 | 20年一遇 |
| B市防洪排涝综合规划 | 2020 | B河 | 100年一遇 | 50年一遇 |

【依据】
1. 文件：《A河流域防洪规划修编报告》
   页码：第45页
   原文片段："A河流域设计暴雨重现期采用50年一遇，防洪标准按20年一遇设计。"

【风险提示】
- 不同区域设计标准差异较大，需结合城市规模和保护对象重要性确定

【建议下一步】
1. 确认项目所在区域的城市等级
2. 核查最新规范版本要求"""
    
    def _mock_flood_answer(self) -> str:
        return """【结论】
当某水库水位超过汛限水位时，应调取以下预案和规程：

1. 《水库防洪调度规程》
2. 《水库大坝安全管理应急预案》
3. 《流域洪水调度方案》

【依据】
1. 文件：《水库防洪调度规程》
   页码：第18页
   原文片段："当水库水位超过汛限水位时，应按照批准的防洪调度方案进行调度。"

【风险提示】
⚠️ 本系统仅提供辅助查询和预案匹配，最终调度决策应由有权限的防汛责任人确认。

【建议下一步】
1. 立即报告防汛责任人
2. 启动水情加密监测"""
    
    def _mock_review_answer(self) -> str:
        return """【一、参数识别表】
| 参数 | 识别结果 | 原文位置 |
|------|---------|---------|
| 工程名称 | 某水库除险加固工程 | 第1页 |
| 工程类型 | 土石坝除险加固 | 第3页 |
| 坝高 | 28.5m | 第5页 |
| 总库容 | 580万m³ | 第5页 |
| 工程等级 | Ⅳ等 | 第6页 |
| 防洪标准 | 50年一遇设计 | 第7页 |

【二、初审结论】
该设计说明书基本完整，主要参数识别清晰，但存在部分需要补充和核实的内容。

【三、疑似风险】
1. 坝高28.5m接近30m界限，需确认是否应按中型水库标准执行
2. 抗震设防参数未明确，需补充地震烈度资料

【四、缺失信息】
1. 缺少工程地质勘察报告
2. 缺少大坝安全鉴定结论

【五、修改建议】
1. 补充地震烈度及抗震设防参数
2. 完善大坝安全鉴定相关内容

【六、规范依据】
1. 《水利水电工程等级划分及洪水标准》SL 252-2017 第3.0.1条
2. 《碾压式土石坝设计规范》SL 274-2020 第4.1.2条"""
    
    def _mock_default_answer(self) -> str:
        return """【结论】
当前知识库资料不足，无法确定您提问的具体答案。

【依据】
无

【建议下一步】
1. 检查问题表述是否清晰
2. 尝试使用不同的关键词组合
3. 联系管理员补充相关资料"""
    
    async def _mock_chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
    ) -> ChatResponse:
        """
        Mock 模式下的 Function Calling。
        根据用户问题内容判断是否需要调用工具，并返回预设的工具调用序列。
        """
        last_user_msg = self._extract_last_user_content(messages)
        tool_names = {self._get_tool_name(t) for t in tools}
        
        # 检查是否已经有工具调用结果（tool角色消息）
        has_tool_result = any(msg.get("role") == "tool" for msg in messages)
        
        # 如果已经有工具结果，直接生成最终回答
        if has_tool_result:
            # 收集工具返回的结果
            tool_results = []
            for msg in messages:
                if msg.get("role") == "tool":
                    try:
                        content = msg.get("content", "{}")
                        if isinstance(content, str):
                            tool_results.append(json.loads(content))
                    except:
                        pass
            
            # 根据工具结果生成最终回答
            final_answer = self._generate_final_answer_from_tools(last_user_msg, tool_results)
            return ChatResponse(
                content=final_answer,
                tool_calls=[],
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
        
        # 简单问答（不含工具触发关键词）直接返回文本回答
        search_keywords = ["规范", "标准", "搜索", "查询", "查找", "找一下", "检索", "有哪些", "GB", "SL", "DL"]
        calc_keywords = ["计算", "参数", "水位", "流量", "坝高", "库容", "高程", "重现期", "算一下", "核算", "等别", "级别", "超高", "安全系数", "防洪标准", "洪水标准", "一遇", "边坡", "堤顶", "坝顶", "几级", "几等"]
        
        needs_search = any(kw in last_user_msg for kw in search_keywords) and "standard_search" in tool_names
        needs_calc = any(kw in last_user_msg for kw in calc_keywords) and "param_calculator" in tool_names
        
        if not needs_search and not needs_calc:
            # 简单问答：直接返回内容，不调用工具
            return ChatResponse(
                content=self._mock_generate(last_user_msg),
                tool_calls=[],
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
        
        # 需要工具调用的场景
        tool_calls: List[ToolCall] = []
        
        if needs_search:
            # 提取搜索关键词
            search_query = self._extract_search_query(last_user_msg)
            tool_calls.append(ToolCall(
                name="standard_search",
                arguments={"query": search_query},
            ))
        
        if needs_calc:
            # 构造计算参数
            calc_params = self._extract_calc_params(last_user_msg)
            tool_calls.append(ToolCall(
                name="param_calculator",
                arguments=calc_params,
            ))
        
        # 工具调用场景下，content 设为 None（表示需要先执行工具）
        return ChatResponse(
            content=None,
            tool_calls=tool_calls,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
    
    def _generate_final_answer_from_tools(self, user_msg: str, tool_results: List[Dict]) -> str:
        """根据工具返回结果生成最终回答"""
        # 查找参数计算结果
        calc_result = None
        for result in tool_results:
            if isinstance(result, dict) and result.get("calc_type"):
                calc_result = result
                break
            if isinstance(result, dict) and result.get("result") and isinstance(result.get("result"), dict):
                inner = result.get("result", {})
                if inner.get("grade") or inner.get("level") or inner.get("min_safety_factor") or inner.get("design_flood") or inner.get("safety_freeboard_m"):
                    calc_result = result
                    break
        
        if calc_result:
            return self._format_calc_result(calc_result, user_msg)
        
        # 查找规范搜索结果
        search_result = None
        for result in tool_results:
            if isinstance(result, dict) and result.get("results"):
                search_result = result
                break
        
        if search_result:
            return self._format_search_result(search_result, user_msg)
        
        # 默认回答
        return self._mock_default_answer()
    
    def _format_calc_result(self, data: Dict, user_msg: str) -> str:
        """格式化参数计算结果为专业回答"""
        result = data.get("result", data)
        code_basis = data.get("code_basis", "")
        note = data.get("note", "")
        calc_type = data.get("calc_type", "")
        
        lines = ["【结论】"]
        
        # 工程等别
        if result.get("grade"):
            grade = result.get("grade")
            grade_name = result.get("grade_name", f"{grade}等")
            scale = result.get("scale", "")
            basis = result.get("basis", "")
            all_inds = result.get("all_indicators", [])
            
            lines.append(f"根据您提供的参数，该工程等别为 **{grade_name}（{scale}）**。")
            if basis:
                lines.append(f"")
                lines.append(f"判定依据：{basis}")
            if all_inds and len(all_inds) > 1:
                lines.append("")
                lines.append("各指标判定结果：")
                for ind in all_inds:
                    lines.append(f"- {ind.get('指标', '')}：{ind.get('判定等别', '')}等（{ind.get('规模', '')}）——{ind.get('依据', '')}")
        
        # 建筑物级别
        elif result.get("level"):
            level = result.get("level")
            btype = result.get("building_type", "建筑物")
            lines.append(f"该工程{btype}级别为 **{level}级**。")
        
        # 防洪标准
        elif result.get("design_flood"):
            df = result.get("design_flood")
            cf = result.get("check_flood", "")
            lines.append(f"设计洪水标准：**{df}**")
            if cf:
                lines.append(f"校核洪水标准：**{cf}**")
        
        # 安全超高
        elif result.get("safety_freeboard_m") is not None:
            fb = result.get("safety_freeboard_m")
            formula = result.get("formula", "")
            fb_note = result.get("note", "")
            condition = result.get("flood_condition", "")
            lt = result.get("levee_type", result.get("dam_type", ""))
            
            if "堤" in calc_type:
                lines.append(f"{lt}{condition}条件下，堤顶安全加高值为 **{fb}m**。")
            else:
                lines.append(f"坝顶安全超高值为 **{fb}m**。")
            if formula:
                lines.append("")
                lines.append(f"计算公式：{formula}")
            if fb_note:
                lines.append("")
                lines.append(fb_note)
        
        # 边坡安全系数
        elif result.get("min_safety_factor") is not None:
            sf = result.get("min_safety_factor")
            cond = result.get("condition", "")
            all_factors = result.get("all_factors", {})
            lines.append(f"{cond}下，边坡抗滑稳定最小安全系数为 **{sf}**。")
            if all_factors:
                lines.append("")
                lines.append("不同工况安全系数要求：")
                for c, f in all_factors.items():
                    lines.append(f"- {c}：{f}")
        
        # 重现期换算
        elif result.get("return_period"):
            rp = result.get("return_period")
            freq = result.get("frequency_pct")
            prob = result.get("annual_exceedance_probability_pct")
            lines.append(f"重现期{rp}年一遇 对应的年超越概率为 **{prob}%**，设计频率为 **{freq}**。")
        
        # 依据
        if code_basis:
            lines.append("")
            lines.append("【依据】")
            lines.append(f"{code_basis}")
        
        # 注意事项
        if note:
            lines.append("")
            lines.append("【注意】")
            lines.append(note)
        
        lines.append("")
        lines.append("⚠️ 风险提示：本计算结果仅供参考，最终设计参数需由具备资质的专业工程师复核确定。")
        
        return "\n".join(lines)
    
    def _format_search_result(self, data: Dict, user_msg: str) -> str:
        """格式化规范搜索结果"""
        results = data.get("results", [])
        count = data.get("result_count", 0)
        
        lines = ["【结论】"]
        if count == 0:
            lines.append("当前知识库中未检索到与您问题直接相关的规范条文。")
            lines.append("")
            lines.append("【建议】")
            lines.append("1. 尝试使用更精确的规范编号或关键词")
            lines.append("2. 联系管理员补充相关规范资料")
            return "\n".join(lines)
        
        lines.append(f"检索到 {count} 条相关规范条文：")
        lines.append("")
        
        for i, r in enumerate(results[:5], 1):
            fname = r.get("file_name", "未知文件")
            page = r.get("page_number", "")
            text = r.get("text", "")
            lines.append(f"[{i}] {fname} {page}")
            lines.append(f"    {text[:300]}")
            lines.append("")
        
        lines.append("【风险提示】")
        lines.append("以上内容为规范条文检索结果，具体应用请结合工程实际情况，由专业工程师判断。")
        
        return "\n".join(lines)
    
    def _extract_search_query(self, text: str) -> str:
        """从用户问题中提取搜索关键词"""
        # 简单启发式：取问题主体作为查询
        for kw in ["请问", "帮我", "查一下", "搜索", "查找", "查询", "找一下", "检索"]:
            text = text.replace(kw, "")
        return text.strip("？?。，, ")[:100] or "水利规范"
    
    def _extract_calc_params(self, text: str) -> Dict[str, Any]:
        """从用户问题中提取计算参数（mock）"""
        # 智能识别计算类型
        calc_type = None
        parameters = {}
        
        # 工程等别判定
        if any(kw in text for kw in ["工程等别", "等别", "规模", "属于几等", "是几等", "什么型"]):
            calc_type = "project_grade"
            # 提取库容
            storage_match = re.search(r"(\d+(?:\.\d+)?)\s*(万m³|万立方米|亿m³|亿立方米)", text)
            if storage_match:
                val = float(storage_match.group(1))
                unit = storage_match.group(2)
                if "亿" in unit:
                    val = val * 10000  # 亿m³转万m³
                parameters["storage"] = val
            # 提取装机容量
            power_match = re.search(r"(\d+(?:\.\d+)?)\s*(MW|万kW|万千瓦|kW)", text)
            if power_match:
                val = float(power_match.group(1))
                unit = power_match.group(2)
                if "万" in unit:
                    val = val * 10
                parameters["power"] = val
            # 提取保护农田
            farmland_match = re.search(r"(\d+(?:\.\d+)?)\s*(万亩|亩)", text)
            if farmland_match:
                val = float(farmland_match.group(1))
                if "万" not in farmland_match.group(2):
                    val = val / 10000
                parameters["farmland"] = val
            # 提取保护人口
            pop_match = re.search(r"(\d+(?:\.\d+)?)\s*(万人|人)", text)
            if pop_match:
                val = float(pop_match.group(1))
                if "万" not in pop_match.group(2):
                    val = val / 10000
                parameters["protect_population"] = val
        
        # 建筑物级别
        elif any(kw in text for kw in ["建筑物级别", "建筑级别", "级别是多少", "几级建筑"]):
            calc_type = "building_level"
            # 提取工程等别
            grade_match = re.search(r"([IVXivx]+)等", text)
            if grade_match:
                grade_roman = grade_match.group(1).upper()
                grade_map = {"I": "I", "II": "II", "III": "III", "IV": "IV", "V": "V"}
                parameters["project_grade"] = grade_map.get(grade_roman, "V")
            else:
                # 尝试中文数字
                if "1" in text or "一" in text:
                    parameters["project_grade"] = "I"
                elif "2" in text or "二" in text:
                    parameters["project_grade"] = "II"
                elif "3" in text or "三" in text:
                    parameters["project_grade"] = "III"
                elif "4" in text or "四" in text:
                    parameters["project_grade"] = "IV"
                elif "5" in text or "五" in text:
                    parameters["project_grade"] = "V"
            parameters["is_main"] = not any(kw in text for kw in ["次要", "临时"])
        
        # 防洪标准
        elif any(kw in text for kw in ["防洪标准", "洪水标准", "设计洪水", "重现期", "一遇"]):
            calc_type = "flood_standard"
            # 提取建筑物级别
            level_match = re.search(r"(\d+)\s*级", text)
            if level_match:
                parameters["building_level"] = int(level_match.group(1))
            # 识别坝型
            if any(kw in text for kw in ["土石坝", "土坝"]):
                parameters["dam_type"] = "earth"
            elif any(kw in text for kw in ["混凝土", "重力坝", "拱坝"]):
                parameters["dam_type"] = "concrete"
        
        # 坝顶超高
        elif any(kw in text for kw in ["坝顶超高", "安全超高", "坝超高", "超高是多少"]):
            calc_type = "dam_freeboard"
            level_match = re.search(r"(\d+)\s*级", text)
            if level_match:
                parameters["building_level"] = int(level_match.group(1))
            if any(kw in text for kw in ["土石坝", "土坝"]):
                parameters["dam_type"] = "earth"
            elif any(kw in text for kw in ["混凝土", "重力坝", "拱坝"]):
                parameters["dam_type"] = "concrete"
        
        # 堤顶超高
        elif any(kw in text for kw in ["堤顶", "堤防超高", "堤超高"]):
            calc_type = "levee_freeboard"
            level_match = re.search(r"(\d+)\s*级", text)
            if level_match:
                parameters["building_level"] = int(level_match.group(1))
            if any(kw in text for kw in ["土堤"]):
                parameters["levee_type"] = "earth"
            else:
                parameters["levee_type"] = "earth"  # 默认土堤
        
        # 边坡安全系数
        elif any(kw in text for kw in ["边坡", "安全系数", "稳定系数"]):
            calc_type = "slope_safety_factor"
            level_match = re.search(r"(\d+)\s*级", text)
            if level_match:
                parameters["building_level"] = int(level_match.group(1))
            if any(kw in text for kw in ["土石坝", "土坝", "堤防"]):
                parameters["dam_type"] = "earth"
            if any(kw in text for kw in ["正常", "设计", "稳定渗流"]):
                parameters["condition"] = "normal"
            elif any(kw in text for kw in ["非常", "校核", "洪水"]):
                parameters["condition"] = "abnormal"
            elif any(kw in text for kw in ["地震"]):
                parameters["condition"] = "earthquake"
        
        # 重现期换算
        elif any(kw in text for kw in ["频率", "概率", "换算", "转换"]):
            calc_type = "return_period_convert"
            rp_match = re.search(r"(\d+)\s*年一遇", text)
            if rp_match:
                parameters["return_period"] = int(rp_match.group(1))
            freq_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            if freq_match:
                parameters["frequency_pct"] = float(freq_match.group(1))
        
        # 默认：尝试判断是否有库容数字
        if calc_type is None:
            storage_match = re.search(r"(\d+(?:\.\d+)?)\s*(万m³|万立方米|亿m³|亿立方米)", text)
            if storage_match:
                calc_type = "project_grade"
                val = float(storage_match.group(1))
                unit = storage_match.group(2)
                if "亿" in unit:
                    val = val * 10000
                parameters["storage"] = val
            else:
                # 还是没识别出来，返回project_grade作为默认
                calc_type = "project_grade"
        
        return {
            "calc_type": calc_type,
            "parameters": parameters,
        }
    
    # ------------------------------------------------------------------
    # 统一 API 调用层（OpenAI / 火山引擎兼容）
    # ------------------------------------------------------------------
    
    def _get_provider_config(self) -> tuple:
        """根据当前 provider 返回 (api_key, base_url)"""
        if self.provider == "openai":
            api_key = settings.OPENAI_API_KEY
            base_url = settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
        elif self.provider == "volcano":
            api_key = settings.VOLCANO_API_KEY
            base_url = settings.VOLCANO_BASE_URL or "https://ark.cn-beijing.volces.com/api/v3"
        else:
            api_key = None
            base_url = None
        return api_key, base_url
    
    def _build_request_body(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """构建统一的请求体"""
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": stream,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        return body
    
    async def _chat_api(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """非流式调用 Chat Completions API，返回文本内容"""
        api_key, base_url = self._get_provider_config()
        if not api_key:
            raise ValueError(f"API Key 未配置 (provider={self.provider})")
        
        body = self._build_request_body(messages, temperature, max_tokens, stream, tools)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            return message.get("content") or ""
    
    async def _chat_api_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 Chat Completions API，解析 SSE 格式逐 token yield。
        
        SSE 格式：data: {"choices": [{"delta": {"content": "..."}}]}\n\n
        结束标记：data: [DONE]\n\n
        """
        api_key, base_url = self._get_provider_config()
        if not api_key:
            raise ValueError(f"API Key 未配置 (provider={self.provider})")
        
        body = self._build_request_body(
            messages, temperature, self.max_tokens, stream=True, tools=tools
        )
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                    # tool_calls 增量在流式场景下暂不展开（复杂场景由 chat_with_tools 处理）
    
    async def _chat_api_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> ChatResponse:
        """非流式调用，解析 tool_calls"""
        api_key, base_url = self._get_provider_config()
        if not api_key:
            raise ValueError(f"API Key 未配置 (provider={self.provider})")
        
        body = self._build_request_body(
            messages, temperature, self.max_tokens, stream=False, tools=tools
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
        
        message = data["choices"][0]["message"]
        content = message.get("content")
        usage_raw = data.get("usage", {})
        usage = {
            "prompt_tokens": usage_raw.get("prompt_tokens", 0),
            "completion_tokens": usage_raw.get("completion_tokens", 0),
            "total_tokens": usage_raw.get("total_tokens", 0),
        }
        
        tool_calls: List[ToolCall] = []
        raw_tool_calls = message.get("tool_calls") or []
        for tc in raw_tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            arguments_str = func.get("arguments", "{}")
            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {"_raw": arguments_str}
            tool_calls.append(ToolCall(name=name, arguments=arguments))
        
        return ChatResponse(content=content, tool_calls=tool_calls, usage=usage)
    
    # ------------------------------------------------------------------
    # 旧接口兼容（内部方法，保留但统一到新 API）
    # ------------------------------------------------------------------
    
    async def _generate_completions(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """统一的非流式生成（替代原来的 _generate_openai / _generate_volcano）"""
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            return await self._chat_api(messages=messages)
        except Exception as e:
            # 修复4：_generate_completions不再静默fallback到mock
            import traceback
            print(f"[LLM] {self.provider} API 调用失败: {e}")
            traceback.print_exc()
            if self.mock_mode or self.provider == "mock":
                return self._mock_generate(prompt)
            raise  # 向上传播异常
    
    async def _generate_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """兼容旧调用（保留）"""
        return await self._generate_completions(prompt, system_prompt)
    
    async def _generate_volcano(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """兼容旧调用（保留）"""
        return await self._generate_completions(prompt, system_prompt)
    
    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    
    def _extract_last_user_content(self, messages: List[Dict[str, str]]) -> str:
        """从消息列表中提取最后一条 user 消息内容"""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                # content 可能是字符串或列表（多模态），这里统一取字符串
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            parts.append(part)
                    return "".join(parts)
        # 如果没有 user 消息，拼接所有内容
        return "\n".join(
            msg.get("content", "") for msg in messages if isinstance(msg.get("content"), str)
        )
    
    @staticmethod
    def _get_tool_name(tool: Dict[str, Any]) -> str:
        """从工具定义中提取名称（兼容 OpenAI function format）"""
        if "function" in tool:
            return tool["function"].get("name", "")
        return tool.get("name", "")
    
    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """格式化检索结果作为上下文"""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            part = f"[{i}] 文件：{chunk.get('file_name', '未知')}\n"
            part += f"页码：{chunk.get('page_number', '未知')}\n"
            # 修复4：兼容旧的"content" key和新的"text" key
            chunk_text = chunk.get('text', '') or chunk.get('content', '')
            part += f"内容：{chunk_text[:500]}\n"
            context_parts.append(part)
        return "\n---\n".join(context_parts)


llm_service = LLMService()
