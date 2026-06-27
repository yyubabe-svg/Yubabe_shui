"""
第二阶段工具API路由：
- 水利计算助手（明渠均匀流、雨水流量、管径校核、堤顶高程、工程量）
- 历史项目复用（相似项目检索、推荐）
- GIS一键出图（基于开源GIS工具）
- CAD图纸检查（DXF解析、图签识别、目录生成）
"""
import os
import math
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_, func
from typing import Optional, List
from pydantic import BaseModel
import datetime

from app.core.database import get_db
from app.models.project import DesignProject, ProjectType, PROJECT_TYPE_NAMES
from app.models.document import Document
from app.models.calc_history import CalcHistory
from app.services.hydraulic_calculator import hydraulic_calculator, calc_result_to_dict

router = APIRouter(prefix="/api/tools", tags=["第二阶段工具"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "exports"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)


# ==================== 请求体模型 ====================

class CalcRequest(BaseModel):
    calc_type: str
    params: dict
    label: Optional[str] = None
    save: bool = True


# ==================== 水利计算助手 ====================

@router.get("/calc/types")
async def list_calc_types():
    """获取所有支持的计算类型"""
    types = hydraulic_calculator.get_calc_types()
    categories = {}
    for t in types:
        cat = t["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    return {
        "categories": [
            {"category": cat, "items": items}
            for cat, items in categories.items()
        ],
        "total": len(types)
    }


@router.post("/calc/compute")
async def run_calculation(
    data: CalcRequest,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """执行一次水利计算"""
    result = hydraulic_calculator.calculate(data.calc_type, data.params)
    result_dict = calc_result_to_dict(result)

    # 保存历史记录
    history_id = None
    if data.save and result.success:
        record = CalcHistory(
            project_id=project_id,
            calc_type=data.calc_type,
            calc_name=result.calc_name,
            category=next((t["category"] for t in hydraulic_calculator.get_calc_types() if t["id"] == data.calc_type), ""),
            input_params=data.params,
            output_values=result.outputs,
            calc_steps=result_dict["steps"],
            code_basis=result.code_basis,
            notes=result.notes,
            warnings=result.warnings,
            label=data.label or result.calc_name,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        history_id = record.id

    return {
        **result_dict,
        "history_id": history_id
    }


@router.get("/calc/history")
async def list_calc_history(
    project_id: Optional[int] = None,
    calc_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """查询计算历史"""
    q = db.query(CalcHistory)
    if project_id:
        q = q.filter(CalcHistory.project_id == project_id)
    if calc_type:
        q = q.filter(CalcHistory.calc_type == calc_type)
    items = q.order_by(desc(CalcHistory.created_at)).limit(limit).all()
    return {
        "items": [
            {
                "id": h.id,
                "project_id": h.project_id,
                "calc_type": h.calc_type,
                "calc_name": h.calc_name,
                "category": h.category,
                "label": h.label,
                "outputs": h.output_values,
                "warnings": h.warnings,
                "code_basis": h.code_basis,
                "is_favorite": h.is_favorite,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in items
        ],
        "total": len(items)
    }


@router.get("/calc/history/{history_id}")
async def get_calc_history(history_id: int, db: Session = Depends(get_db)):
    """获取单条计算历史详情"""
    h = db.query(CalcHistory).filter(CalcHistory.id == history_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="计算记录不存在")
    return {
        "id": h.id,
        "project_id": h.project_id,
        "calc_type": h.calc_type,
        "calc_name": h.calc_name,
        "category": h.category,
        "label": h.label,
        "inputs": h.input_params,
        "outputs": h.output_values,
        "steps": h.calc_steps,
        "code_basis": h.code_basis,
        "notes": h.notes,
        "warnings": h.warnings,
        "is_favorite": h.is_favorite,
        "output_filename": h.output_filename,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }


@router.delete("/calc/history/{history_id}")
async def delete_calc_history(history_id: int, db: Session = Depends(get_db)):
    """删除计算记录"""
    h = db.query(CalcHistory).filter(CalcHistory.id == history_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="计算记录不存在")
    db.delete(h)
    db.commit()
    return {"success": True}


# ==================== 历史项目复用 ====================

@router.get("/history/similar")
async def find_similar_projects(
    project_type: Optional[str] = None,
    location_keyword: Optional[str] = None,
    river_basin_keyword: Optional[str] = None,
    min_flood_standard: Optional[int] = None,
    max_flood_standard: Optional[int] = None,
    project_type_name_keyword: Optional[str] = None,
    exclude_project_id: Optional[int] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    相似历史项目检索
    基于项目类型、地理位置、流域、防洪标准等匹配
    """
    q = db.query(DesignProject)
    # 不严格过滤status，所有项目都可作为参考（排除archived）
    q = q.filter(DesignProject.status != "archived")

    if exclude_project_id:
        q = q.filter(DesignProject.id != exclude_project_id)
    if project_type:
        q = q.filter(DesignProject.project_type == project_type)
    if location_keyword:
        kw = f"%{location_keyword}%"
        q = q.filter(or_(
            DesignProject.location.ilike(kw),
            DesignProject.project_name.ilike(kw),
        ))
    if river_basin_keyword:
        kw = f"%{river_basin_keyword}%"
        q = q.filter(DesignProject.river_basin.ilike(kw))
    if project_type_name_keyword:
        kw = f"%{project_type_name_keyword}%"
        q = q.filter(DesignProject.project_name.ilike(kw))

    projects = q.order_by(desc(DesignProject.created_at)).limit(limit * 2).all()

    # 评分排序（简单评分：类型匹配=30分，位置/流域关键词=20分/个）
    scored = []
    for p in projects:
        score = 0
        reasons = []
        if project_type and p.project_type == project_type:
            score += 30
            reasons.append(f"项目类型匹配：{PROJECT_TYPE_NAMES.get(p.project_type, p.project_type)}")
        if location_keyword and p.location and location_keyword in p.location:
            score += 25
            reasons.append(f"位置关键词匹配：{p.location}")
        if river_basin_keyword and p.river_basin and river_basin_keyword in p.river_basin:
            score += 20
            reasons.append(f"流域关键词匹配：{p.river_basin}")
        if project_type_name_keyword and project_type_name_keyword in p.project_name:
            score += 15
            reasons.append(f"项目名称包含关键词")
        # 项目文档数量作为丰富度参考
        doc_count = db.query(func.count(Document.id)).filter(Document.project_id == p.id).scalar() or 0
        richness = min(doc_count * 3, 15)
        score += richness
        if doc_count > 0:
            reasons.append(f"包含{doc_count}份参考文档")
        scored.append((score, reasons, p))

    scored.sort(key=lambda x: -x[0])
    top = scored[:limit]

    return {
        "items": [
            {
                "id": p.id,
                "project_code": p.project_code,
                "project_name": p.project_name,
                "project_type": p.project_type,
                "project_type_name": PROJECT_TYPE_NAMES.get(p.project_type, p.project_type),
                "design_stage": p.design_stage,
                "location": p.location,
                "river_basin": p.river_basin,
                "total_investment": p.total_investment,
                "doc_count": db.query(func.count(Document.id)).filter(Document.project_id == p.id).scalar() or 0,
                "match_score": s,
                "match_reasons": r,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for s, r, p in top
        ],
        "total": len(top)
    }


@router.get("/history/recommend-for-project/{project_id}")
async def recommend_for_project(
    project_id: int,
    limit: int = 6,
    db: Session = Depends(get_db)
):
    """为指定项目智能推荐相似历史项目"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 从项目中提取关键词
    location_parts = (project.location or "").replace("市", "").replace("区", "").replace("县", "")
    # 取前2-3个字符作为地域关键词
    location_kw = location_parts[:2] if len(location_parts) >= 2 else location_parts

    return await find_similar_projects(
        project_type=project.project_type,
        location_keyword=location_kw if location_kw else None,
        river_basin_keyword=None,
        exclude_project_id=project_id,
        limit=limit,
        db=db
    )


@router.get("/history/reuse-materials/{project_id}")
async def get_project_reuse_materials(project_id: int, db: Session = Depends(get_db)):
    """获取历史项目可复用资料清单（文档、章节、计算、表格）"""
    project = db.query(DesignProject).filter(DesignProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    docs = db.query(Document).filter(Document.project_id == project_id).order_by(Document.created_at).all()
    calcs = db.query(CalcHistory).filter(CalcHistory.project_id == project_id).order_by(CalcHistory.created_at).limit(20).all()

    return {
        "project": {
            "id": project.id,
            "project_name": project.project_name,
            "project_type": project.project_type,
            "project_type_name": PROJECT_TYPE_NAMES.get(project.project_type, project.project_type),
            "location": project.location,
        },
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "file_type": d.file_type,
                "is_report": d.is_report,
                "chapter_count": len(d.chapter_json) if d.chapter_json else 0,
                "table_count": d.table_count,
                "total_pages": d.total_pages,
            }
            for d in docs
        ],
        "calculations": [
            {
                "id": c.id,
                "calc_type": c.calc_type,
                "calc_name": c.calc_name,
                "label": c.label,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in calcs
        ]
    }


# ==================== CAD 图纸检查（第一阶段：图签识别+目录生成） ====================

@router.post("/cad/check-drawings")
async def check_cad_drawings(
    files: List[UploadFile] = File(...),
):
    """
    批量检查CAD图纸
    解析DXF文件图签，检查图号连续性、图名缺失、日期/专业/负责人一致性
    返回图纸目录清单和问题列表
    """
    results = []
    issues = []

    for idx, file in enumerate(files):
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".dxf"]:
            issues.append({
                "file": file.filename,
                "severity": "warning",
                "message": f"非DXF文件({ext})，跳过解析",
            })
            results.append({
                "filename": file.filename,
                "parse_status": "skipped",
                "reason": "unsupported_format"
            })
            continue

        # 保存文件
        safe_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # 解析DXF（使用ezdxf）
        drawing_info = {
            "filename": file.filename,
            "file_size": len(content),
            "drawing_number": None,
            "drawing_name": None,
            "scale": None,
            "date": None,
            "designer": None,
            "reviewer": None,
            "chief": None,
            "major": None,
            "project_name": None,
            "stage": None,
            "texts_found": 0,
            "blocks_found": 0,
            "parse_status": "parsed",
        }

        try:
            import ezdxf
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()

            # 收集所有TEXT/MTEXT实体
            all_texts = []
            for entity in msp:
                if entity.dxftype() == "TEXT":
                    txt = entity.dxf.text.strip()
                    if txt:
                        all_texts.append(txt)
                elif entity.dxftype() == "MTEXT":
                    txt = entity.text.strip()
                    if txt:
                        all_texts.append(txt)

            # 收集块引用数
            block_refs = [e for e in msp if e.dxftype() == "INSERT"]
            drawing_info["texts_found"] = len(all_texts)
            drawing_info["blocks_found"] = len(block_refs)

            # 简单启发式提取图签信息
            # 图号通常是"图号"、"图别"或"编号"后面的文本，或者是S-01、SS-01等格式
            import re
            full_text = "\n".join(all_texts)

            # 图号匹配：图号 XX-XX 或 图号：XX 或 编号：XX
            dn_match = re.search(r"(?:图\s*号|编\s*号|图\s*别)\s*[:：]?\s*([A-Za-z0-9\-—/]+)", full_text)
            if dn_match:
                drawing_info["drawing_number"] = dn_match.group(1).strip()
            else:
                # 匹配结尾的编号格式，如 S-01、水施-03
                dn_match2 = re.search(r"\b([A-Z]{1,3}[\-—]\s*\d{1,3}(?:[\-—]\d{1,3})?)\b", full_text)
                if dn_match2:
                    drawing_info["drawing_number"] = dn_match2.group(1).strip()

            # 图名：通常在标题栏中间位置较大文字，简化：找"图名"后面的文字
            name_match = re.search(r"(?:图\s*名|名\s*称)\s*[:：]?\s*([^\n]{2,30})", full_text)
            if name_match:
                drawing_info["drawing_name"] = name_match.group(1).strip()
            else:
                # 若没有明确标记，取长度较长的中文文本作为候选
                chinese_texts = [t for t in all_texts if len(t) >= 4 and re.search(r"[\u4e00-\u9fa5]", t)]
                if chinese_texts:
                    drawing_info["drawing_name"] = max(chinese_texts, key=len)[:30]

            # 比例
            scale_match = re.search(r"(?:比\s*例|SCALE)\s*[:：]?\s*([0-9]+\s*[:：]\s*[0-9]+)", full_text, re.IGNORECASE)
            if scale_match:
                drawing_info["scale"] = scale_match.group(1).replace(" ", "")

            # 日期
            date_match = re.search(r"(20\d{2})[\.\-/年](\d{1,2})[\.\-/月](\d{1,2})", full_text)
            if date_match:
                drawing_info["date"] = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"

            # 设计/校核/审查
            role_map = {"设计": "designer", "制图": "designer", "校核": "reviewer", "审核": "reviewer",
                        "审查": "chief", "审定": "chief", "项目负责人": "chief"}
            for role_cn, role_en in role_map.items():
                m = re.search(rf"{role_cn}\s*[:：]?\s*([\u4e00-\u9fa5]{2,4})", full_text)
                if m and not drawing_info.get(role_en):
                    drawing_info[role_en] = m.group(1).strip()

            # 专业
            major_match = re.search(r"(?:专\s*业)\s*[:：]?\s*([\u4e00-\u9fa5]{2,5})", full_text)
            if major_match:
                drawing_info["major"] = major_match.group(1).strip()

        except ImportError:
            drawing_info["parse_status"] = "ezdxf_not_installed"
            drawing_info["warnings"] = ["未安装ezdxf库，无法解析DXF；建议运行 pip install ezdxf"]
            issues.append({
                "file": file.filename,
                "severity": "warning",
                "message": "ezdxf库未安装，返回基本文件信息",
            })
        except Exception as e:
            drawing_info["parse_status"] = "error"
            drawing_info["error"] = str(e)
            issues.append({
                "file": file.filename,
                "severity": "error",
                "message": f"DXF解析失败：{str(e)[:100]}",
            })

        results.append(drawing_info)

        # 清理临时文件
        try:
            os.remove(file_path)
        except:
            pass

    # 一致性检查
    # 1. 图号连续性
    numbers = []
    for r in results:
        if r.get("drawing_number"):
            # 尝试提取末尾数字
            num_match = re.search(r"(\d+)\s*$", r["drawing_number"])
            if num_match:
                numbers.append((r["drawing_number"], int(num_match.group(1)), r["filename"]))
    numbers.sort(key=lambda x: x[1])
    if len(numbers) >= 2:
        num_set = {n[1] for n in numbers}
        expected = set(range(min(num_set), max(num_set) + 1))
        missing = expected - num_set
        for m in sorted(missing):
            issues.append({
                "severity": "major",
                "message": f"图号不连续：缺少编号尾号 {m}",
            })

    # 2. 图名缺失
    for r in results:
        if r["parse_status"] == "parsed" and not r.get("drawing_name"):
            issues.append({
                "file": r["filename"],
                "severity": "major",
                "message": "未识别到图名，请检查图签",
            })

    # 3. 专业/日期/负责人一致性检查（若多数图纸有值）
    for field in ["date", "designer", "reviewer", "chief", "major"]:
        values = [r.get(field) for r in results if r.get(field)]
        if len(values) >= max(2, len(results) // 2):
            from collections import Counter
            most_common = Counter(values).most_common(1)[0]
            if most_common[1] < len(values):
                inconsistent = [r["filename"] for r in results if r.get(field) and r[field] != most_common[0]]
                for fn in inconsistent:
                    issues.append({
                        "file": fn,
                        "severity": "minor",
                        "message": f"{field}字段不一致（多数为{most_common[0]}，此文件为{next(r[field] for r in results if r['filename']==fn and r.get(field))}）",
                    })

    # 生成图纸目录
    catalog = sorted(
        [r for r in results if r["parse_status"] in ("parsed", "ezdxf_not_installed")],
        key=lambda x: (x.get("drawing_number") or "~")
    )

    return {
        "total_files": len(files),
        "parsed_count": sum(1 for r in results if r["parse_status"] == "parsed"),
        "drawings": results,
        "catalog": [
            {
                "index": i + 1,
                "drawing_number": d.get("drawing_number") or "待补",
                "drawing_name": d.get("drawing_name") or "待识别",
                "scale": d.get("scale") or "—",
                "major": d.get("major") or "—",
                "date": d.get("date") or "—",
                "filename": d["filename"],
            }
            for i, d in enumerate(catalog)
        ],
        "issues": issues,
        "summary": {
            "total": len(results),
            "issues_total": len(issues),
            "issues_critical": sum(1 for i in issues if i["severity"] == "error"),
            "issues_major": sum(1 for i in issues if i["severity"] == "major"),
            "issues_minor": sum(1 for i in issues if i["severity"] == "minor"),
            "issues_warning": sum(1 for i in issues if i["severity"] == "warning"),
        }
    }


@router.get("/cad/check-templates")
async def list_cad_check_templates():
    """CAD图签检查规则模板列表"""
    return {
        "templates": [
            {
                "id": "standard_title_block",
                "name": "标准图签（国标）",
                "desc": "符合GB/T 14689-2008的标准标题栏",
                "required_fields": ["图号", "图名", "比例", "日期", "设计", "校核", "审核", "专业"],
            },
            {
                "id": "water_conservancy",
                "name": "水利行业图签",
                "desc": "水利水电工程制图标准SL 73，含阶段、项目名称等",
                "required_fields": ["图号", "图名", "比例", "日期", "设计", "校核", "审查", "项目名称", "阶段"],
            }
        ]
    }


# ==================== GIS 一键出图（第一阶段：基础空间分析） ====================

@router.post("/gis/analyze")
async def gis_analyze(
    files: List[UploadFile] = File(...),
    analysis_type: str = Query("basic", description="分析类型: basic(基础统计), slope(坡度), watershed(汇水), flood(淹没)"),
):
    """
    GIS空间分析（轻量版：基于GeoPandas/Rasterio）
    上传SHP/ZIP/GeoJSON/DEM数据，返回分析结果和图件
    """
    try:
        import geopandas as gpd
        import json as json_mod
    except ImportError:
        return {
            "success": False,
            "message": "GIS依赖未安装",
            "install_hint": "pip install geopandas rasterio shapely pyproj",
            "fallback": {
                "analysis_type": analysis_type,
                "note": "当前环境未安装GIS库，返回文件基础信息。安装后可进行坡度/汇水/淹没等分析。"
            }
        }

    results = []
    output_dir = os.path.join(EXPORT_DIR, "gis", datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(output_dir, exist_ok=True)

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        safe_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        info = {
            "filename": file.filename,
            "file_size": len(content),
            "ext": ext,
            "status": "processed",
        }

        try:
            if ext in [".shp", ".geojson", ".json", ".zip", ".gpkg"]:
                gdf = gpd.read_file(file_path)
                info["feature_count"] = len(gdf)
                info["geometry_type"] = list(gdf.geom_type.unique()) if len(gdf) > 0 else []
                info["crs"] = str(gdf.crs) if gdf.crs else None
                info["bounds"] = list(gdf.total_bounds) if len(gdf) > 0 else None
                info["columns"] = list(gdf.columns)

                # 计算面积/长度（若是多边形/线）
                if len(gdf) > 0:
                    # 转换为等积投影计算面积
                    try:
                        gdf_proj = gdf.to_crs(epsg=3857) if gdf.crs else gdf
                        if any(gdf.geom_type.str.contains("Polygon")):
                            info["area_km2"] = round(gdf_proj.geometry.area.sum() / 1e6, 4)
                        if any(gdf.geom_type.str.contains("LineString")):
                            info["length_km"] = round(gdf_proj.geometry.length.sum() / 1000, 4)
                    except:
                        pass

                # 属性表前5行预览
                info["attribute_preview"] = gdf.head(5).drop(columns=["geometry"], errors="ignore").to_dict(orient="records")

            elif ext in [".tif", ".tiff", ".dem", ".asc"]:
                import rasterio
                from rasterio.warp import transform_bounds
                with rasterio.open(file_path) as src:
                    info["raster_width"] = src.width
                    info["raster_height"] = src.height
                    info["crs"] = str(src.crs)
                    info["bounds"] = list(src.bounds)
                    info["resolution"] = list(src.res)
                    info["band_count"] = src.count
                    band1 = src.read(1, masked=True)
                    info["min_value"] = float(band1.min()) if band1.count() > 0 else None
                    info["max_value"] = float(band1.max()) if band1.count() > 0 else None
                    info["mean_value"] = float(band1.mean()) if band1.count() > 0 else None

                    if analysis_type == "slope":
                        try:
                            import numpy as np
                            # 简化坡度计算（度）
                            dy, dx = np.gradient(band1.filled(0), src.res[0], src.res[1])
                            slope = np.degrees(np.arctan(np.sqrt(dx * dx + dy * dy)))
                            info["slope_min"] = float(slope.min())
                            info["slope_max"] = float(slope.max())
                            info["slope_mean"] = float(slope.mean())
                            # 坡度分级
                            info["slope_classes"] = {
                                "0-5°(平地)": float((slope < 5).sum() / slope.size * 100),
                                "5-15°(缓坡)": float(((slope >= 5) & (slope < 15)).sum() / slope.size * 100),
                                "15-25°(中坡)": float(((slope >= 15) & (slope < 25)).sum() / slope.size * 100),
                                "25-35°(陡坡)": float(((slope >= 25) & (slope < 35)).sum() / slope.size * 100),
                                ">35°(急坡)": float((slope >= 35).sum() / slope.size * 100),
                            }
                        except Exception as e:
                            info["slope_error"] = str(e)
            else:
                info["status"] = "unsupported"
                info["message"] = f"暂不支持的文件格式：{ext}"
        except Exception as e:
            info["status"] = "error"
            info["error"] = str(e)

        results.append(info)
        try:
            os.remove(file_path)
        except:
            pass

    return {
        "success": True,
        "analysis_type": analysis_type,
        "file_count": len(files),
        "results": results,
        "supported_formats": {
            "vector": [".shp(+shx/dbf/prj)", ".geojson", ".gpkg", ".zip(shp打包)"],
            "raster": [".tif/.tiff", ".dem", ".asc"],
        },
        "future_features": [
            "自动生成项目位置图（叠加行政区划、水系）",
            "流域范围提取与汇水面积统计",
            "DEM坡度/坡向分析图",
            "洪水淹没范围快速模拟",
            "出图为可插入报告的PNG/PDF",
        ]
    }


@router.get("/gis/info")
async def gis_info():
    """GIS模块能力说明"""
    gis_available = False
    try:
        import geopandas
        gis_available = True
    except ImportError:
        pass

    return {
        "module": "GIS一键出图助手",
        "status": "available" if gis_available else "limited",
        "capabilities_phase2": [
            "矢量数据基本统计（面积、长度、要素数量）",
            "DEM基础统计（高程范围、坡度分级）",
            "数据格式识别与属性预览",
        ],
        "capabilities_future": [
            "项目位置图自动生成",
            "流域范围/汇水分区图",
            "坡度分析图",
            "洪水淹没范围模拟(SFINCS)",
            "图件导出PNG/PDF",
        ],
        "dependencies": {
            "geopandas": "pip install geopandas",
            "rasterio": "pip install rasterio",
            "shapely": "pip install shapely",
            "pyproj": "pip install pyproj",
        }
    }
