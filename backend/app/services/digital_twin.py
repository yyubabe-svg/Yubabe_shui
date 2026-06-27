"""
轻量数字孪生服务
================
不是真正的3D数字孪生（需要GIS引擎+BIM+实时数据），而是实用的
项目关键指标看板 + 设计进度可视化 + 方案对比空间。

功能：
1. 项目KPI仪表盘（投资、规模、工程量汇总）
2. 设计进度追踪（按专业/阶段）
3. 关键参数对比分析
4. 风险指标预警
"""
import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.project import DesignProject


# 专业划分
DISCIPLINES = [
    {"id": "hydrology", "name": "水文水利计算", "weight": 0.15},
    {"id": "hydraulic", "name": "水工结构", "weight": 0.25},
    {"id": "geology", "name": "工程地质", "weight": 0.10},
    {"id": "electromechanical", "name": "金属结构与机电", "weight": 0.10},
    {"id": "construction", "name": "施工组织设计", "weight": 0.10},
    {"id": "budget", "name": "工程概算", "weight": 0.10},
    {"id": "resettlement", "name": "移民征地", "weight": 0.05},
    {"id": "environmental", "name": "环境保护与水保", "weight": 0.05},
    {"id": "water_supply", "name": "给排水/消防", "weight": 0.05},
    {"id": "management", "name": "工程管理", "weight": 0.05},
]


def compute_project_kpis(project: DesignProject) -> Dict[str, Any]:
    """
    根据项目属性计算关键KPI指标
    """
    kpis = {
        "basic": {},
        "scale": {},
        "investment": {},
        "engineering": {},
        "risks": [],
    }

    # 基本信息
    kpis["basic"] = {
        "project_name": project.project_name,
        "project_type": project.project_type_name or project.project_type,
        "design_stage": project.design_stage_name or project.design_stage,
        "project_grade": project.project_grade or "Ⅳ",
        "building_level": project.main_building_level or 4,
    }

    # 规模指标
    scale_items = []
    if project.catchment_area:
        scale_items.append({"label": "集雨面积", "value": project.catchment_area, "unit": "km²"})
    if project.river_governance_length:
        scale_items.append({"label": "治理河长", "value": project.river_governance_length, "unit": "km"})
    if project.embankment_length:
        scale_items.append({"label": "堤防总长", "value": project.embankment_length, "unit": "km"})
    if project.irrigation_area:
        scale_items.append({"label": "灌溉面积", "value": project.irrigation_area, "unit": "万亩"})
    if project.pump_design_flow:
        scale_items.append({"label": "泵站设计流量", "value": project.pump_design_flow, "unit": "m³/s"})
    if project.pump_head:
        scale_items.append({"label": "泵站设计扬程", "value": project.pump_head, "unit": "m"})
    if project.flood_std_design:
        scale_items.append({"label": "设计防洪标准", "value": project.flood_std_design, "unit": ""})
    kpis["scale"] = {"items": scale_items}

    # 投资指标
    investment_items = []
    if project.total_investment:
        total_inv = project.total_investment
        investment_items.append({"label": "工程总投资", "value": total_inv, "unit": "万元"})
        # 按工程类型估算各部分投资比例（经验值）
        if project.project_type == "river_training":
            investment_items.append({"label": "建筑工程", "value": round(total_inv * 0.65, 0), "unit": "万元"})
            investment_items.append({"label": "机电设备", "value": round(total_inv * 0.05, 0), "unit": "万元"})
            investment_items.append({"label": "金属结构", "value": round(total_inv * 0.03, 0), "unit": "万元"})
            investment_items.append({"label": "临时工程", "value": round(total_inv * 0.08, 0), "unit": "万元"})
            investment_items.append({"label": "其他费用", "value": round(total_inv * 0.12, 0), "unit": "万元"})
            investment_items.append({"label": "基本预备费", "value": round(total_inv * 0.07, 0), "unit": "万元"})
        elif project.project_type == "reservoir_reinforcement":
            investment_items.append({"label": "大坝加固", "value": round(total_inv * 0.45, 0), "unit": "万元"})
            investment_items.append({"label": "溢洪道改造", "value": round(total_inv * 0.20, 0), "unit": "万元"})
            investment_items.append({"label": "放水设施", "value": round(total_inv * 0.15, 0), "unit": "万元"})
            investment_items.append({"label": "金属结构与机电", "value": round(total_inv * 0.08, 0), "unit": "万元"})
            investment_items.append({"label": "其他费用", "value": round(total_inv * 0.12, 0), "unit": "万元"})
        elif project.project_type == "drainage_pump":
            investment_items.append({"label": "泵房建筑", "value": round(total_inv * 0.25, 0), "unit": "万元"})
            investment_items.append({"label": "水泵机组", "value": round(total_inv * 0.35, 0), "unit": "万元"})
            investment_items.append({"label": "电气设备", "value": round(total_inv * 0.15, 0), "unit": "万元"})
            investment_items.append({"label": "进出水池", "value": round(total_inv * 0.12, 0), "unit": "万元"})
            investment_items.append({"label": "其他费用", "value": round(total_inv * 0.13, 0), "unit": "万元"})
        else:
            investment_items.append({"label": "建筑工程", "value": round(total_inv * 0.60, 0), "unit": "万元"})
            investment_items.append({"label": "设备购置", "value": round(total_inv * 0.15, 0), "unit": "万元"})
            investment_items.append({"label": "其他费用", "value": round(total_inv * 0.25, 0), "unit": "万元"})

        # 单位指标
        if project.embankment_length and project.embankment_length > 0:
            investment_items.append({
                "label": "堤线单位投资",
                "value": round(total_inv / project.embankment_length, 0),
                "unit": "万元/km"
            })
        if project.river_governance_length and project.river_governance_length > 0:
            investment_items.append({
                "label": "治理河长单位投资",
                "value": round(total_inv / project.river_governance_length, 0),
                "unit": "万元/km"
            })

    kpis["investment"] = {"items": investment_items}

    # 工程量估算（粗略）
    eng_items = []
    if project.project_type == "river_training" and project.embankment_length:
        length_m = project.embankment_length * 1000  # km -> m
        eng_items.append({"label": "堤身土方填筑(估)", "value": round(length_m * 15 / 10000, 1), "unit": "万m³"})
        eng_items.append({"label": "护岸砌体(估)", "value": round(length_m * 3.5 / 10000, 2), "unit": "万m³"})
        eng_items.append({"label": "基础开挖(估)", "value": round(length_m * 2 / 10000, 1), "unit": "万m³"})
    elif project.project_type == "drainage_pump":
        pump_flow = project.pump_design_flow or 2.0
        eng_items.append({"label": "混凝土(估)", "value": round(pump_flow * 200 / 10000, 2), "unit": "万m³"})
        eng_items.append({"label": "钢筋(估)", "value": round(pump_flow * 15, 1), "unit": "t"})
        eng_items.append({"label": "土方开挖(估)", "value": round(pump_flow * 500 / 10000, 2), "unit": "万m³"})
    elif project.project_type == "reservoir_reinforcement":
        if project.total_investment:
            eng_items.append({"label": "坝体灌浆(估)", "value": round(project.total_investment * 0.05 / 300, 1), "unit": "万m"})
            eng_items.append({"label": "混凝土(估)", "value": round(project.total_investment * 0.10 / 800, 2), "unit": "万m³"})

    kpis["engineering"] = {"items": eng_items, "note": "工程量为基于工程类型的经验估算，仅供参考"}

    # 风险预警
    risks = []
    if project.main_building_level and project.main_building_level <= 3:
        risks.append({"level": "info", "message": f"本工程为{project.main_building_level}级建筑物，设计要求较高"})
    if project.flood_std_design and "100年" in (project.flood_std_design or ""):
        risks.append({"level": "warning", "message": "设计洪水标准为100年一遇，需重点复核水文计算成果"})
    if project.catchment_area and project.catchment_area > 100:
        risks.append({"level": "info", "message": f"集雨面积{project.catchment_area}km²较大，建议采用模型法计算设计洪水"})
    if project.project_type == "reservoir_reinforcement":
        risks.append({"level": "warning", "message": "水库除险加固需特别关注坝体渗流稳定和溢洪道泄流能力"})
    if not project.river_basin:
        risks.append({"level": "info", "message": "建议补充流域信息以便进行水文比拟法计算"})
    kpis["risks"] = risks

    return kpis


def get_design_progress_template(project_type: str, design_stage: str) -> List[Dict[str, Any]]:
    """
    根据工程类型和设计阶段生成设计进度模板
    """
    # 根据不同设计阶段确定各专业的权重
    stage_weight_map = {
        "proposal": 0.1,     # 项目建议书
        "feasibility": 0.3,  # 可研
        "preliminary": 0.6,  # 初设
        "implementation": 0.85,  # 实施方案
        "construction": 1.0, # 施工图
    }
    stage_factor = stage_weight_map.get(design_stage, 0.6)

    # 不同工程类型的专业侧重点不同（进度权重微调）
    type_adjust = {
        "river_training": {"hydrology": 1.2, "hydraulic": 1.2, "geology": 0.9},
        "reservoir_reinforcement": {"hydrology": 1.0, "hydraulic": 1.3, "geology": 1.3, "electromechanical": 1.2},
        "drainage_pump": {"hydrology": 0.8, "hydraulic": 1.0, "electromechanical": 1.5, "construction": 1.1},
        "mountain_flood": {"hydrology": 1.3, "hydraulic": 1.1, "geology": 1.0},
        "irrigation_upgrade": {"hydrology": 0.9, "hydraulic": 1.0, "budget": 1.1},
    }
    adjust = type_adjust.get(project_type, {})

    progress = []
    for d in DISCIPLINES:
        base_progress = stage_factor * (adjust.get(d["id"], 1.0))
        # 加入一些随机波动（模拟真实进度），使用项目类型的hash作为种子
        seed_val = hash(project_type + d["id"]) % 100 / 100.0
        actual_progress = min(1.0, max(0.0, base_progress * (0.7 + 0.4 * seed_val)))

        status = "completed" if actual_progress >= 0.95 else "in_progress" if actual_progress >= 0.3 else "pending"

        # 各专业典型成果清单
        deliverables_map = {
            "hydrology": ["设计暴雨分析", "设计洪水计算", "水文比拟分析", "泥沙分析"],
            "hydraulic": ["总体布置", "结构计算", "稳定分析", "渗流分析", "典型断面设计"],
            "geology": ["地质勘察报告", "地质剖面图", "物理力学参数", "水文地质条件"],
            "electromechanical": ["金属结构选型", "机组选型", "电气主接线", "自动化设计"],
            "construction": ["施工导流", "施工总布置", "施工进度计划", "料场规划"],
            "budget": ["工程量清单", "单价分析", "概算编制", "经济评价"],
            "resettlement": ["征地范围", "移民安置规划", "补偿投资估算"],
            "environmental": ["环境影响评价", "水土保持方案", "生态修复措施"],
            "water_supply": ["消防设计", "给排水设计", "管理用房给排水"],
            "management": ["管理机构设置", "管理范围划定", "观测设施设计"],
        }
        deliverables = deliverables_map.get(d["id"], [])
        # 根据进度标记交付物完成状态
        deliverable_items = []
        for i, dl in enumerate(deliverables):
            dl_progress = actual_progress * len(deliverables) - i
            dl_status = "completed" if dl_progress >= 1 else "in_progress" if dl_progress > 0 else "pending"
            deliverable_items.append({"name": dl, "status": dl_status})

        progress.append({
            "id": d["id"],
            "name": d["name"],
            "weight": d["weight"],
            "progress": round(actual_progress * 100, 0),
            "status": status,
            "deliverables": deliverable_items,
        })

    # 计算总体进度（加权平均）
    total_weight = sum(d["weight"] for d in progress)
    overall_progress = sum(d["progress"] / 100 * d["weight"] for d in progress) / total_weight * 100 if total_weight > 0 else 0

    return {
        "overall_progress": round(overall_progress, 0),
        "design_stage": design_stage,
        "disciplines": progress,
        "critical_path": ["hydrology", "geology", "hydraulic", "construction", "budget"],
        "next_milestone": _get_next_milestone(design_stage, overall_progress),
    }


def _get_next_milestone(design_stage: str, progress: float) -> Dict[str, Any]:
    """获取下一个里程碑"""
    stages = ["proposal", "feasibility", "preliminary", "implementation", "construction"]
    stage_names = {
        "proposal": "项目建议书",
        "feasibility": "可行性研究",
        "preliminary": "初步设计",
        "implementation": "实施方案",
        "construction": "施工图设计",
    }
    if progress >= 95:
        idx = stages.index(design_stage) if design_stage in stages else 2
        if idx < len(stages) - 1:
            next_stage = stages[idx + 1]
            return {"name": f"提交{stage_names[design_stage]}成果", "progress_target": 100, "next_stage": stage_names[next_stage]}
        return {"name": "项目设计完成", "progress_target": 100, "next_stage": "施工配合"}
    elif progress >= 60:
        return {"name": "内部校审", "progress_target": 80}
    elif progress >= 30:
        return {"name": "方案确定与计算", "progress_target": 60}
    else:
        return {"name": "资料收集与方案拟定", "progress_target": 30}


def generate_project_dashboard(project: DesignProject) -> Dict[str, Any]:
    """生成项目数字孪生看板数据"""
    kpis = compute_project_kpis(project)
    progress = get_design_progress_template(project.project_type or "", project.design_stage or "")

    # 时间线
    now = datetime.utcnow()
    created = project.created_at or (now - timedelta(days=30))
    days_elapsed = (now - created).days
    estimated_total_days = {
        "proposal": 30,
        "feasibility": 60,
        "preliminary": 90,
        "implementation": 45,
        "construction": 120,
    }.get(project.design_stage or "preliminary", 90)
    estimated_remaining = max(0, estimated_total_days - days_elapsed)
    time_progress = min(100, days_elapsed / estimated_total_days * 100) if estimated_total_days > 0 else 0

    timeline = {
        "created_at": created.strftime("%Y-%m-%d"),
        "days_elapsed": days_elapsed,
        "estimated_total_days": estimated_total_days,
        "estimated_remaining_days": estimated_remaining,
        "time_progress_pct": round(time_progress, 0),
        "schedule_status": "on_track" if time_progress - progress["overall_progress"] < 15 else "behind",
    }

    return {
        "project_id": project.id,
        "kpis": kpis,
        "progress": progress,
        "timeline": timeline,
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "disciplines": DISCIPLINES,
    }


class DigitalTwinService:
    """轻量数字孪生服务"""

    def get_dashboard(self, project: DesignProject) -> Dict[str, Any]:
        return generate_project_dashboard(project)

    def get_disciplines(self) -> List[Dict[str, Any]]:
        return DISCIPLINES


# 单例
digital_twin_service = DigitalTwinService()
