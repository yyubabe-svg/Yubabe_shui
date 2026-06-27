from .base import BaseTool, ToolCallResult, ToolParameter
from .registry import ToolRegistry, tool_registry

# 工具类导入
from .standard_search import StandardSearchTool
from .param_calculator import ParamCalculatorTool
from .rag_query import RAGQueryTool
from .code_lookup import CodeLookupTool
from .project_matcher import ProjectMatcherTool
from .flood_plan_query import FloodPlanQueryTool
from .compliance_checker import ComplianceCheckerTool
from .doc_generator import DocGeneratorTool
from .cad_helper import CadHelperTool

# 工具提示词
from .prompts import TOOL_USAGE_TIPS

__all__ = [
    "BaseTool",
    "ToolCallResult",
    "ToolParameter",
    "ToolRegistry",
    "tool_registry",
    "StandardSearchTool",
    "ParamCalculatorTool",
    "RAGQueryTool",
    "CodeLookupTool",
    "ProjectMatcherTool",
    "FloodPlanQueryTool",
    "ComplianceCheckerTool",
    "DocGeneratorTool",
    "CadHelperTool",
    "TOOL_USAGE_TIPS",
]


def register_all_tools() -> None:
    """注册所有工具实例到全局注册表"""
    tools = [
        StandardSearchTool(),
        ParamCalculatorTool(),
        RAGQueryTool(),
        CodeLookupTool(),
        ProjectMatcherTool(),
        FloodPlanQueryTool(),
        ComplianceCheckerTool(),
        DocGeneratorTool(),
        CadHelperTool(),
    ]
    for tool in tools:
        tool_registry.register(tool)
