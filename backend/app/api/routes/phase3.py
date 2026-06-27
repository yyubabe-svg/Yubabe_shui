"""
第三阶段工具API路由：
- 水文模型辅助（SWMM输入生成、设计暴雨、RPT报告解析）
- 参数化设计（堤防/渠道断面参数化设计、多方案对比）
- 轻量数字孪生（项目KPI看板、设计进度可视化）
"""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.project import DesignProject
from app.services.hydro_model_assistant import hydro_model_assistant
from app.services.parametric_design import parametric_design_service
from app.services.digital_twin import digital_twin_service

router = APIRouter(prefix="/api/phase3", tags=["第三阶段工具"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==================== 请求体模型 ====================

class RainfallGenRequest(BaseModel):
    city: str = "成都"
    return_period: float = 20
    duration_min: float = 120
    timestep_min: float = 5
    r_factor: float = 0.4


class SwmmInpRequest(BaseModel):
    project_name: str = "未命名项目"
    subcatchments: List[dict] = []
    junctions: List[dict] = []
    conduits: List[dict] = []
    outfalls: List[dict] = []
    rain_gauge: Optional[dict] = None


class SectionDesignRequest(BaseModel):
    section_type: str = "trapezoidal"
    design_water_level: float = 100
    bed_elevation: float = 95
    bed_width: float = 10
    m_slope: float = 2.0
    revetment_type: str = "stone_mortar"
    freeboard: float = 1.0
    crest_width: float = 5.0
    berm_width: float = 2.0
    foundation_depth: float = 0.6


class SchemeCompareRequest(BaseModel):
    schemes: List[dict]


# ==================== 水文模型辅助接口 ====================

@router.get("/hydro/models")
async def list_hydro_models():
    """获取支持的水文模型列表"""
    return {
        "models": hydro_model_assistant.get_supported_models(),
        "supported_cities": [
            "成都", "乐山", "绵阳", "德阳", "眉山", "自贡", "内江", "遂宁", "广元", "雅安",
            "重庆", "北京", "上海", "广州"
        ]
    }


@router.post("/hydro/rainfall/generate")
async def generate_design_rainfall(req: RainfallGenRequest):
    """生成设计暴雨（芝加哥雨型）"""
    result = hydro_model_assistant.generate_rainfall(req.model_dump())
    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors)
    return {
        "success": True,
        "model_type": result.model_type,
        "operation": result.operation,
        "data": result.data,
        "warnings": result.warnings,
        "notes": result.notes,
    }


@router.post("/hydro/swmm/generate-inp")
async def generate_swmm_inp(req: SwmmInpRequest, project_id: Optional[int] = None):
    """生成SWMM .inp输入文件"""
    params = req.model_dump()
    result = hydro_model_assistant.generate_swmm_input(params)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors)
    return {
        "success": True,
        "model_type": result.model_type,
        "operation": result.operation,
        "data": result.data,
        "warnings": result.warnings,
        "notes": result.notes,
    }


@router.post("/hydro/swmm/parse-rpt")
async def parse_swmm_rpt(
    file: UploadFile = File(...),
    project_id: Optional[int] = Query(None),
):
    """解析SWMM .rpt报告文件"""
    content = await file.read()
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = content.decode("gbk", errors="ignore")

    result = hydro_model_assistant.parse_swmm_report(text)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors)
    return {
        "success": True,
        "model_type": result.model_type,
        "operation": result.operation,
        "filename": file.filename,
        "data": result.data,
        "warnings": result.warnings,
        "errors": result.errors,
    }


@router.get("/hydro/subcatchment/params")
async def recommend_subcatchment_params(
    land_use: str = Query("residential"),
    area_ha: float = Query(1.0),
):
    """推荐子汇水区参数"""
    return hydro_model_assistant.recommend_subcatchment_params(land_use, area_ha)


@router.get("/hydro/swmm/options")
async def get_swmm_options():
    """获取SWMM建模选项（用地类型、管材等）"""
    data = hydro_model_assistant.generate_swmm_input(
        project_name="__options__", subcatchments=[], junctions=[], conduits=[], outfalls=[]
    )
    return {
        "land_use_options": data.data.get("land_use_options", []),
        "conduit_material_options": data.data.get("conduit_material_options", []),
        "supported_cities": data.data.get("supported_cities", []),
    }


# ==================== 参数化设计接口 ====================

@router.get("/parametric/options")
async def get_parametric_options(building_level: int = Query(4)):
    """获取参数化设计选项"""
    return {
        "section_types": parametric_design_service.get_section_types(),
        "revetment_types": parametric_design_service.get_revetment_types(),
        "recommendations": parametric_design_service.get_recommendations(building_level),
    }


@router.post("/parametric/design-section")
async def design_section(req: SectionDesignRequest, project_id: Optional[int] = Query(None)):
    """执行参数化断面设计"""
    result = parametric_design_service.design_section(req.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "设计失败"))
    return result


@router.post("/parametric/compare")
async def compare_schemes(req: SchemeCompareRequest):
    """多方案对比"""
    result = parametric_design_service.compare_design_schemes(req.schemes)
    return result


# ==================== 轻量数字孪生接口 ====================

@router.get("/digital-twin/dashboard/{project_id}")
async def get_project_dashboard(project_id: int, db: Session = Depends(get_db)):
    """获取项目数字孪生看板数据"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return digital_twin_service.get_dashboard(project)


@router.get("/digital-twin/disciplines")
async def get_disciplines():
    """获取专业列表"""
    return {"disciplines": digital_twin_service.get_disciplines()}
