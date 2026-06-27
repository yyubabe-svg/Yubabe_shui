from typing import Dict, Any
from .base import BaseTool, ToolCallResult, ToolParameter


class DocGeneratorTool(BaseTool):
    name = "doc_generator"
    description = "文档生成工具，支持生成ISO体系文档、审查报告、设计大纲等水利工程文档。需要用户提供必要的项目信息。"
    parameters = [
        ToolParameter(name="doc_type", type="string", description="文档类型：'iso'(ISO体系附表)、'review_report'(审查报告)、'design_outline'(设计大纲)", required=True, enum=["iso", "review_report", "design_outline"]),
        ToolParameter(name="params", type="object", description="文档参数字典，包含项目名称、业主单位、设计阶段等信息", required=True),
    ]

    async def ainvoke(self, doc_type: str, params: Dict[str, Any], **kwargs) -> ToolCallResult:
        try:
            doc_type_names = {
                "iso": "ISO管理体系附表",
                "review_report": "合规审查报告",
                "design_outline": "设计大纲",
            }

            # 检查必要参数
            required = ["project_name"]
            missing = [p for p in required if p not in params]
            if missing:
                return ToolCallResult(
                    success=False,
                    error=f"缺少必要参数：{', '.join(missing)}。请先向用户确认这些信息。",
                )

            return ToolCallResult(
                success=True,
                data={
                    "doc_type": doc_type,
                    "doc_type_name": doc_type_names.get(doc_type, doc_type),
                    "status": "ready",
                    "params": params,
                    "instruction": f"已收集到项目信息，可以生成{doc_type_names.get(doc_type)}。文档生成功能需要在前端ISO页面上传完整设计报告后自动填充。请告知用户：如需生成完整文档，请前往「ISO体系」页面上传项目设计报告。",
                    "preview_info": {
                        "项目名称": params.get("project_name", ""),
                        "设计阶段": params.get("design_stage", "待确认"),
                        "业主单位": params.get("client", "待确认"),
                    },
                },
                references=[],
            )
        except Exception as e:
            return ToolCallResult(success=False, error=str(e))
