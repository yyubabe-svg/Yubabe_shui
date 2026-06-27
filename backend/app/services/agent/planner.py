"""任务规划器（简化版本，后续迭代完善DAG任务分解）"""
from typing import List, Dict, Any, Optional


class TaskPlanner:
    """简单任务规划器"""
    
    def __init__(self):
        pass
    
    def analyze_task(self, user_message: str) -> Dict[str, Any]:
        """分析任务复杂度"""
        # 简单判断：包含多个需求或需要多工具的视为复杂任务
        complex_keywords = ["并且", "同时", "然后", "另外", "还", "也", "生成.*审查", "审查.*生成"]
        is_complex = any(kw in user_message for kw in complex_keywords)
        
        return {
            "is_complex": is_complex,
            "subtasks": [],
            "recommended_tools": self._recommend_tools(user_message),
        }
    
    def _recommend_tools(self, message: str) -> List[str]:
        """根据消息内容推荐工具"""
        recommended = []
        msg = message.lower()
        
        if any(k in msg for k in ["规范", "标准", "规程", "怎么规定", "要求"]):
            recommended.append("standard_search")
        if any(k in msg for k in ["计算", "级别", "等别", "标准", "超高", "重现期", "是多少"]):
            recommended.append("param_calculator")
        if any(k in msg for k in ["案例", "类似", "参考", "工程"]):
            recommended.append("project_matcher")
        if any(k in msg for k in ["防汛", "预案", "应急", "水位", "响应"]):
            recommended.append("flood_plan_query")
        if any(k in msg for k in ["第.*条", "GB ", "SL ", "DL "]):
            recommended.append("code_lookup")
        if any(k in msg for k in ["生成", "文档", "iso", "报告"]):
            recommended.append("doc_generator")
        if any(k in msg for k in ["cad", "模型", "三维", "构件"]):
            recommended.append("cad_helper")
        
        if not recommended:
            recommended.append("rag_query")
        
        return recommended


planner = TaskPlanner()
