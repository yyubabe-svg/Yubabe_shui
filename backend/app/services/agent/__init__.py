# Agent模块初始化
from app.services.agent.tools import tool_registry


def register_all_tools():
    """注册所有内置工具"""
    from app.services.agent.tools.rag_query import RAGQueryTool
    from app.services.agent.tools.standard_search import StandardSearchTool
    from app.services.agent.tools.param_calculator import ParamCalculatorTool
    from app.services.agent.tools.code_lookup import CodeLookupTool
    from app.services.agent.tools.project_matcher import ProjectMatcherTool
    from app.services.agent.tools.flood_plan_query import FloodPlanQueryTool
    from app.services.agent.tools.compliance_checker import ComplianceCheckerTool
    from app.services.agent.tools.doc_generator import DocGeneratorTool
    from app.services.agent.tools.cad_helper import CadHelperTool

    tool_registry.register(RAGQueryTool())
    tool_registry.register(StandardSearchTool())
    tool_registry.register(ParamCalculatorTool())
    tool_registry.register(CodeLookupTool())
    tool_registry.register(ProjectMatcherTool())
    tool_registry.register(FloodPlanQueryTool())
    tool_registry.register(ComplianceCheckerTool())
    tool_registry.register(DocGeneratorTool())
    tool_registry.register(CadHelperTool())


# 自动注册
register_all_tools()

from app.services.agent.agent_service import agent_service
from app.services.agent.reactor import react_engine

__all__ = ["agent_service", "react_engine", "tool_registry", "register_all_tools"]
