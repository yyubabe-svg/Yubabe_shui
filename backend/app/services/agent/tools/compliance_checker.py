from .base import BaseTool, ToolCallResult, ToolParameter


class ComplianceCheckerTool(BaseTool):
    name = "compliance_checker"
    description = "合规审查工具，对设计文档内容或参数进行合规性初审，检查是否符合水利规范要求。建议先使用standard_search获取相关规范条文后再综合判断"
    parameters = [
        ToolParameter(name="content", type="string", description="需要审查的设计内容或参数字符串", required=True),
        ToolParameter(name="check_items", type="string", description="需要重点审查的项目，如'坝顶高程'、'防洪标准'、'边坡稳定'等，多个项目用逗号分隔", required=False, default=""),
    ]

    async def ainvoke(self, content: str, check_items: str = "", **kwargs) -> ToolCallResult:
        # 注意：实际审查逻辑需要结合规范检索和LLM判断
        # 这里返回提示，让Agent先调用standard_search获取相关规范再综合分析
        return ToolCallResult(
            success=True,
            data={
                "status": "需要结合规范检索",
                "content_summary": content[:200] + ("..." if len(content) > 200 else ""),
                "check_items": check_items,
                "instruction": "请使用standard_search工具检索相关规范条文，然后根据规范要求对以下内容进行合规性审查，列出问题、依据和建议",
                "review_focus": check_items.split(",") if check_items else ["防洪标准", "建筑物级别", "结构安全", "边坡稳定"],
            },
            references=[],
        )
