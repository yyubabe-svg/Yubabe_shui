"""
第四阶段工具API路由：
- 成果导出（工程量清单Excel、设计说明书Word）
- 三维可视化辅助（未来扩展）
"""
import os
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.project import DesignProject
from app.models.user_usage import UserUsage
from app.api.routes.usage import get_current_user
from app.services.export_service import export_service
from app.services.parametric_design import parametric_design_service
from app.services.hydro_model_assistant import hydro_model_assistant

router = APIRouter(prefix="/api/phase4", tags=["第四阶段工具"])


# ==================== 请求体模型 ====================

class SectionDesignInput(BaseModel):
    section_type: str = "trapezoidal"
    design_water_level: float = 100
    bed_elevation: float = 95
    bed_width: float = 10
    m_slope: float = 2.0
    revetment_type: str = "stone_mortar"
    freeboard: float = 1.0
    crest_width: float = 5.0
    foundation_depth: float = 0.6
    # 矩形断面参数
    wall_thickness: Optional[float] = 0.6
    wall_bottom_thickness: Optional[float] = 1.8
    wall_height: Optional[float] = 6.0
    # 复式断面参数
    main_channel_width: Optional[float] = 15
    main_channel_depth: Optional[float] = 3.5
    floodplain_width: Optional[float] = 20
    m_slope_main: Optional[float] = 2.0
    m_slope_flood: Optional[float] = 2.5
    floodplain_revetment: Optional[str] = "grass"


class RainfallExportInput(BaseModel):
    city: str = "成都"
    return_period: float = 20
    duration_min: float = 120
    timestep_min: float = 5


class ExportRequest(BaseModel):
    sections: List[SectionDesignInput]
    channel_lengths: Optional[List[float]] = None
    include_report: bool = True
    include_boq: bool = True
    rainfall: Optional[RainfallExportInput] = None


# ==================== 导出接口 ====================

@router.get("/export/options")
async def get_export_options(user: UserUsage = Depends(get_current_user)):
    """获取导出选项（需认证）"""
    return {
        "export_formats": [
            {"id": "boq_excel", "name": "工程量清单(Excel)", "ext": ".xlsx", "desc": "含分部分项工程量、主要材料汇总"},
            {"id": "design_report", "name": "设计说明书(Word)", "ext": ".docx", "desc": "含综合说明、水文、地质、建筑物设计、施工、投资估算等章节"},
        ],
        "section_types": parametric_design_service.get_section_types(),
    }


@router.post("/export/boq")
async def export_boq(
    req: ExportRequest,
    project_id: Optional[int] = Query(None),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出工程量清单 Excel（需认证，同步操作用to_thread包裹）"""
    # 获取项目信息
    project_name = "未命名项目"
    project_info = {}
    if project_id:
        project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
        if project:
            project_name = project.project_name
            project_info = {
                "project_grade": getattr(project, 'project_grade', 'Ⅳ') or 'Ⅳ',
                "building_level": getattr(project, 'main_building_level', 4) or 4,
                "design_stage": project.design_stage_name or project.design_stage or '初步设计',
                "location": project.location or '',
                "project_type": project.project_type_name or project.project_type or '河道治理',
                "total_investment": project.total_investment,
            }

    # 执行各断面设计
    section_results = []
    for sec in req.sections:
        result = await asyncio.to_thread(parametric_design_service.design_section, sec.model_dump())
        if result.get("success"):
            section_results.append(result)

    if not section_results:
        raise HTTPException(status_code=400, detail="没有有效的断面设计结果")

    lengths = req.channel_lengths or [1000] * len(section_results)
    if len(lengths) < len(section_results):
        lengths = lengths + [1000] * (len(section_results) - len(lengths))

    return await asyncio.to_thread(
        export_service.export_bill_of_quantities,
        project_name, section_results, lengths[:len(section_results)], project_info
    )


@router.post("/export/report")
async def export_report(
    req: ExportRequest,
    project_id: Optional[int] = Query(None),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出设计说明书 Word（需认证，同步操作用to_thread包裹）"""
    project_name = "未命名项目"
    project_info = {}
    if project_id:
        project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
        if project:
            project_name = project.project_name
            project_info = {
                "project_grade": getattr(project, 'project_grade', 'Ⅳ') or 'Ⅳ',
                "building_level": getattr(project, 'main_building_level', 4) or 4,
                "design_stage": project.design_stage_name or project.design_stage or '初步设计',
                "location": project.location or '',
                "project_type": project.project_type_name or project.project_type or '河道治理',
                "flood_std_design": "20年一遇",
                "flood_std_check": "50年一遇",
                "catchment_area": getattr(project, 'catchment_area', None),
                "river_governance_length": getattr(project, 'river_governance_length', None),
                "embankment_length": getattr(project, 'embankment_length', None),
                "total_investment": project.total_investment,
            }

    # 执行断面设计
    section_results = []
    for sec in req.sections:
        result = await asyncio.to_thread(parametric_design_service.design_section, sec.model_dump())
        if result.get("success"):
            section_results.append(result)

    # 设计暴雨结果
    rainfall_result = None
    if req.rainfall:
        try:
            rainfall_result = await asyncio.to_thread(hydro_model_assistant.generate_rainfall, req.rainfall.model_dump())
            if hasattr(rainfall_result, 'success'):
                rainfall_result = {
                    "success": rainfall_result.success,
                    "data": rainfall_result.data,
                }
        except Exception:
            pass

    return await asyncio.to_thread(
        export_service.export_design_report,
        project_name, project_info, section_results, None, rainfall_result
    )


@router.post("/export/all")
async def export_all(
    req: ExportRequest,
    rainfall: Optional[RainfallExportInput] = None,
    project_id: Optional[int] = Query(None),
    user: UserUsage = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    一键导出全部成果（返回zip压缩包，包含Excel+Word）
    注意：此接口需要安装zipstream，暂返回单独文件列表信息
    """
    return {
        "message": "请分别调用 /export/boq 和 /export/report 接口下载",
        "endpoints": ["/api/phase4/export/boq", "/api/phase4/export/report"]
    }
