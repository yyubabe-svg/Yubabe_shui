from .base import BaseTool, ToolCallResult, ToolParameter


class CadHelperTool(BaseTool):
    name = "cad_helper"
    description = "CAD辅助工具，提供水利工程构件的CAD设计建议、参数化建模提示词生成指导，推荐合适的构件类型"
    parameters = [
        ToolParameter(name="component", type="string", description="水利构件类型，如'拱坝'、'重力坝'、'溢洪道'、'水闸'、'堤防'、'渡槽'等", required=True),
        ToolParameter(name="description", type="string", description="设计需求描述，如尺寸、功能要求等", required=False, default=""),
    ]

    async def ainvoke(self, component: str, description: str = "", **kwargs) -> ToolCallResult:
        cad_templates = {
            "拱坝": {"icon": "🏔️", "category": "挡水建筑物", "tip": "混凝土拱坝需关注拱端推力、坝肩稳定、倒悬度控制"},
            "重力坝": {"icon": "🧱", "category": "挡水建筑物", "tip": "重力坝断面设计需满足抗滑稳定、坝体应力要求，注意坝基扬压力"},
            "土石坝": {"icon": "⛰️", "category": "挡水建筑物", "tip": "土石坝需关注渗流稳定、坝坡稳定、防渗体与反滤层设计"},
            "溢洪道": {"icon": "🌊", "category": "泄水建筑物", "tip": "溢洪道需计算泄流能力、消能防冲，控制堰型选择"},
            "水闸": {"icon": "🚪", "category": "泄水建筑物", "tip": "水闸需关注防渗排水、消能防冲、地基处理、闸门启闭力"},
            "堤防": {"icon": "🏞️", "category": "防洪工程", "tip": "堤防设计需确定堤顶高程、堤身断面、渗流稳定、边坡防护"},
            "渡槽": {"icon": "🌉", "category": "输水建筑物", "tip": "渡槽需进行水力计算、结构内力分析、槽身与支撑结构设计"},
            "涵洞": {"icon": "🕳️", "category": "输水建筑物", "tip": "涵洞需确定洞径、纵坡、进出口形式，注意防渗和接缝处理"},
            "泵站": {"icon": "💧", "category": "排灌工程", "tip": "泵站需计算设计流量、扬程、机组选型、进出水池设计"},
        }

        info = cad_templates.get(component, None)

        if info:
            return ToolCallResult(
                success=True,
                data={
                    "component": component,
                    "icon": info["icon"],
                    "category": info["category"],
                    "design_tip": info["tip"],
                    "description": description,
                    "cadam_prompt_guide": "生成CAD提示词时，应包含：构件类型、主要尺寸参数（可调参数）、工程细节、结构特征",
                    "next_step": "如需生成三维CAD模型，请前往「智能CAD」页面选择对应模板或输入描述自动生成提示词。",
                },
                references=[],
            )
        else:
            return ToolCallResult(
                success=True,
                data={
                    "component": component,
                    "available_components": list(cad_templates.keys()),
                    "suggestion": f"未找到'{component}'的预置模板。可用构件类型：{', '.join(cad_templates.keys())}。您可以前往「智能CAD」页面用自然语言描述您的需求，系统将自动生成参数化建模提示词。",
                },
                references=[],
            )
