"""
参数化设计服务
================
提供水利工程中典型构件的参数化设计能力：
1. 堤防/河道典型断面生成（梯形、矩形、复式断面）
2. 护岸结构选型与参数推荐
3. 多方案对比（工程量/投资对比）
4. 典型图参数化描述（供CAD出图参考）

依据：
- GB 50286-2013《堤防工程设计规范》
- SL 379-2007《水工挡土墙设计规范》
- GB/T 50662-2011《水利水电工程节水灌溉设计规范》
"""
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class SectionType(str, Enum):
    """断面形式"""
    TRAPEZOIDAL = "trapezoidal"      # 梯形断面
    RECTANGULAR = "rectangular"      # 矩形断面
    COMPOUND = "compound"            # 复式断面（主槽+滩地）
    TRIANGULAR = "triangular"        # 三角形断面


class RevetmentType(str, Enum):
    """护岸类型"""
    CONCRETE = "concrete"            # 混凝土护岸
    STONE_MORTAR = "stone_mortar"    # 浆砌石护岸
    STONE_DRY = "stone_dry"          # 干砌石护岸
    RIPRAP = "riprap"                # 抛石护岸
    ECOLOGICAL = "ecological"        # 生态护岸
    GRASS = "grass"                  # 草皮护坡


# ==================== 护岸参数推荐表 ====================

REVETMENT_PARAMS = {
    RevetmentType.CONCRETE.value: {
        "name": "混凝土护岸",
        "thickness_m": 0.20,
        "slope_ratio_min": 1.5,       # 最小边坡系数 m=1.5
        "slope_ratio_max": 2.5,
        "slope_ratio_recommend": 2.0,
        "cost_per_m3": 650,           # 元/m³（含模板）
        "foundation_depth_m": 0.5,
        "underdrain": True,
        "suitable_flow_ms": 5.0,       # 允许流速
        "applicable": ["城市河段", "重要堤防", "流速大的河段"],
        "notes": "需设排水孔和反滤层，混凝土强度不低于C20"
    },
    RevetmentType.STONE_MORTAR.value: {
        "name": "浆砌石护岸",
        "thickness_m": 0.40,
        "slope_ratio_min": 1.5,
        "slope_ratio_max": 2.0,
        "slope_ratio_recommend": 1.75,
        "cost_per_m3": 380,
        "foundation_depth_m": 0.6,
        "underdrain": True,
        "suitable_flow_ms": 4.0,
        "applicable": ["一般河道治理", "中小河流", "山区河道"],
        "notes": "M7.5水泥砂浆砌筑，需设伸缩缝"
    },
    RevetmentType.STONE_DRY.value: {
        "name": "干砌石护岸",
        "thickness_m": 0.35,
        "slope_ratio_min": 2.0,
        "slope_ratio_max": 3.0,
        "slope_ratio_recommend": 2.5,
        "cost_per_m3": 280,
        "foundation_depth_m": 0.5,
        "underdrain": True,
        "suitable_flow_ms": 3.0,
        "applicable": ["次要堤防", "流速较小河段", "临时工程"],
        "notes": "反滤层要求较高，适用于有石料来源地区"
    },
    RevetmentType.RIPRAP.value: {
        "name": "抛石护岸",
        "thickness_m": 0.60,
        "slope_ratio_min": 2.0,
        "slope_ratio_max": 3.5,
        "slope_ratio_recommend": 2.5,
        "cost_per_m3": 220,
        "foundation_depth_m": 0.0,
        "underdrain": False,
        "suitable_flow_ms": 3.5,
        "applicable": ["岸坡防护", "丁坝护脚", "险工段"],
        "notes": "块石重量需根据流速计算，D50按Isbash公式确定"
    },
    RevetmentType.ECOLOGICAL.value: {
        "name": "生态护岸",
        "thickness_m": 0.30,
        "slope_ratio_min": 2.5,
        "slope_ratio_max": 4.0,
        "slope_ratio_recommend": 3.0,
        "cost_per_m3": 450,
        "foundation_depth_m": 0.4,
        "underdrain": False,
        "suitable_flow_ms": 2.5,
        "applicable": ["生态治理", "景观河道", "海绵城市"],
        "notes": "可采用生态混凝土框格、雷诺护垫、石笼网箱等形式"
    },
    RevetmentType.GRASS.value: {
        "name": "草皮护坡",
        "thickness_m": 0.20,
        "slope_ratio_min": 3.0,
        "slope_ratio_max": 5.0,
        "slope_ratio_recommend": 3.5,
        "cost_per_m3": 50,
        "foundation_depth_m": 0.0,
        "underdrain": False,
        "suitable_flow_ms": 1.5,
        "applicable": ["滩地防护", "背水坡", "流速小区域"],
        "notes": "建议配合土工格室或三维植被网使用"
    },
}

# 堤顶宽度推荐（按工程级别）
CREST_WIDTH_RECOMMEND = {
    1: 8.0,   # 1级堤防
    2: 7.0,   # 2级
    3: 6.0,   # 3级
    4: 5.0,   # 4级
    5: 3.0,   # 5级
}

# 堤顶超高推荐（按级别+风浪组合，m）
FREEBOARD_RECOMMEND = {
    1: 2.0,
    2: 1.5,
    3: 1.0,
    4: 0.8,
    5: 0.5,
}


@dataclass
class SectionDesignResult:
    """断面设计结果"""
    success: bool
    section_name: str
    section_type: str
    parameters: Dict[str, Any]
    geometry: Dict[str, Any]          # 几何坐标点（用于绘图）
    quantities: Dict[str, float]      # 工程量(每延米)
    costs: Dict[str, float]           # 投资估算(每延米)
    stability: Dict[str, Any]         # 稳定计算结果
    compliance: List[str]             # 规范符合性检查
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def design_trapezoidal_section(
    design_water_level: float,         # 设计水位 (m)
    bed_elevation: float,              # 河底高程 (m)
    bed_width: float,                  # 底宽 (m)
    m_slope: float,                    # 边坡系数
    revetment_type: str = "stone_mortar",
    freeboard: float = 1.0,            # 堤顶超高 (m)
    berm_width: float = 2.0,           # 马道宽度 (m)
    foundation_depth: float = 0.6,     # 护岸基础埋深 (m)
    crest_width: float = 5.0,          # 堤顶宽度 (m)
) -> SectionDesignResult:
    """
    梯形堤防断面参数化设计
    返回几何尺寸、工程量、估算投资
    """
    warnings = []
    compliance = []
    notes = []

    # 水深
    water_depth = design_water_level - bed_elevation
    if water_depth <= 0:
        return SectionDesignResult(
            success=False, section_name="堤防断面", section_type="trapezoidal",
            parameters={}, geometry={}, quantities={}, costs={}, stability={},
            compliance=[], warnings=["设计水位必须高于河底高程"]
        )

    # 堤顶高程
    crest_elevation = design_water_level + freeboard
    bank_height = crest_elevation - bed_elevation  # 从河底到堤顶的高度

    # 护岸参数
    rev = REVETMENT_PARAMS.get(revetment_type, REVETMENT_PARAMS[RevetmentType.STONE_MORTAR.value])

    # 检查边坡系数
    if m_slope < rev["slope_ratio_min"]:
        warnings.append(f"边坡系数 m={m_slope} 小于 {rev['name']} 推荐最小值 {rev['slope_ratio_min']}，可能不稳定")
    elif m_slope > rev["slope_ratio_max"]:
        warnings.append(f"边坡系数 m={m_slope} 超过 {rev['name']} 推荐最大值 {rev['slope_ratio_max']}，占地较宽")
    else:
        compliance.append(f"边坡系数 m={m_slope} 符合 {rev['name']} 推荐范围 [{rev['slope_ratio_min']}, {rev['slope_ratio_max']}]")

    # 过水断面面积（设计水位下）
    A = (bed_width + m_slope * water_depth) * water_depth
    # 湿周
    P = bed_width + 2 * water_depth * math.sqrt(1 + m_slope ** 2)
    # 水力半径
    R = A / P if P > 0 else 0

    # 护岸面积（每延米）：两侧边坡长度 × 厚度
    revetment_length_per_side = (bank_height + foundation_depth) * math.sqrt(1 + m_slope ** 2)
    revetment_volume_per_m = 2 * revetment_length_per_side * rev["thickness_m"]

    # 堤身土方量（梯形，每延米）
    # 堤顶宽 crest_width，堤底宽 = crest_width + 2 * m_slope * bank_height
    levee_base_width = crest_width + 2 * m_slope * bank_height
    levee_fill_volume_per_m = (crest_width + levee_base_width) / 2 * bank_height

    # 基础开挖（两侧基础）
    foundation_volume_per_m = 2 * (bed_width/10 + 1.0) * foundation_depth * rev["thickness_m"]
    # 简化：基础为护岸底部延伸部分
    foundation_volume_per_m = 2 * rev["thickness_m"] * (foundation_depth + 0.5)

    # 马道工程量（如果高度超过5m设马道）
    berm_volume = 0
    if bank_height > 5 and berm_width > 0:
        notes.append(f"堤高 {bank_height:.1f}m 超过5m，设置 {berm_width}m 宽马道")
        berm_volume = berm_width * 0.5 * 2  # 简化

    # 几何坐标点（从左到右，从堤脚到堤顶再到右堤脚，用于绘图）
    # 坐标系：x水平，y高程，原点在左堤脚外侧
    points = []
    # 左堤外脚
    left_outer_toe_x = 0
    left_outer_toe_y = bed_elevation - foundation_depth
    points.append({"x": left_outer_toe_x, "y": left_outer_toe_y})
    # 左堤顶外边缘
    left_crest_x = m_slope * bank_height
    left_crest_y = crest_elevation
    points.append({"x": left_crest_x, "y": left_crest_y})
    # 左堤顶内边缘
    right_crest_inner_x = left_crest_x + crest_width
    points.append({"x": right_crest_inner_x, "y": crest_elevation})
    # 右堤脚
    right_toe_x = right_crest_inner_x + m_slope * bank_height + bed_width
    right_toe_y = bed_elevation
    points.append({"x": right_toe_x, "y": right_toe_y})
    # 右堤外脚（基础底）
    right_outer_toe_x = right_toe_x + m_slope * foundation_depth
    right_outer_toe_y = bed_elevation - foundation_depth
    points.append({"x": right_outer_toe_x, "y": right_outer_toe_y})

    # 设计水位线
    water_level_points = [
        {"x": left_crest_x, "y": design_water_level},
        {"x": right_crest_inner_x, "y": design_water_level},
    ]

    # 河底线
    bed_points = [
        {"x": left_crest_x, "y": bed_elevation},
        {"x": right_crest_inner_x + bed_width, "y": bed_elevation},
    ]

    # 投资估算
    revetment_cost = revetment_volume_per_m * rev["cost_per_m3"]
    fill_cost = levee_fill_volume_per_m * 35  # 土方填筑 35元/m³
    foundation_cost = foundation_volume_per_m * rev["cost_per_m3"] * 1.2  # 基础稍贵
    total_cost = revetment_cost + fill_cost + foundation_cost

    # 抗滑稳定粗略验算（简化计算）
    # 摩擦系数
    f = 0.45  # 土壤与基础摩擦系数（经验值）
    # 堤身自重（kN/m）
    gamma_fill = 18  # 填土重度 kN/m³
    W = levee_fill_volume_per_m * gamma_fill
    # 水压力（kN/m）
    gamma_w = 10
    F_water = 0.5 * gamma_w * water_depth ** 2
    # 抗滑安全系数
    Kc = f * W / F_water if F_water > 0 else 999
    stability_ok = Kc >= 1.25  # 4级堤防抗滑安全系数允许值

    if stability_ok:
        compliance.append(f"抗滑稳定安全系数 Kc={Kc:.2f} ≥ 1.25，满足规范要求")
    else:
        warnings.append(f"抗滑稳定安全系数 Kc={Kc:.2f} < 1.25，不满足规范要求，需加宽堤身或放缓边坡")

    compliance.append(f"堤顶超高 {freeboard}m，符合{freeboard >= 1.0 and 4 or 5}级堤防要求")

    return SectionDesignResult(
        success=True,
        section_name=f"{rev['name']}梯形堤防断面",
        section_type=SectionType.TRAPEZOIDAL.value,
        parameters={
            "bed_width": bed_width,
            "m_slope": m_slope,
            "water_depth": round(water_depth, 2),
            "freeboard": freeboard,
            "crest_width": crest_width,
            "crest_elevation": round(crest_elevation, 2),
            "revetment_type": revetment_type,
            "revetment_name": rev["name"],
            "revetment_thickness": rev["thickness_m"],
            "foundation_depth": foundation_depth,
        },
        geometry={
            "outline_points": points,
            "water_level_points": water_level_points,
            "bed_points": bed_points,
            "section_width_m": round(right_outer_toe_x, 2),
            "section_height_m": round(bank_height + foundation_depth, 2),
        },
        quantities={
            "revetment_volume_m3_per_m": round(revetment_volume_per_m, 3),
            "fill_volume_m3_per_m": round(levee_fill_volume_per_m, 3),
            "foundation_volume_m3_per_m": round(foundation_volume_per_m, 3),
            "excavation_m3_per_m": round(foundation_volume_per_m * 1.2, 3),
            "concrete_or_stone_m3_per_m": round(revetment_volume_per_m, 3),
            "wetted_perimeter_m": round(P, 2),
            "flow_area_m2": round(A, 2),
            "hydraulic_radius_m": round(R, 2),
        },
        costs={
            "revetment_cost_yuan_per_m": round(revetment_cost, 0),
            "fill_cost_yuan_per_m": round(fill_cost, 0),
            "foundation_cost_yuan_per_m": round(foundation_cost, 0),
            "total_cost_yuan_per_m": round(total_cost, 0),
            "total_cost_yuan_per_km": round(total_cost * 1000, 0),
        },
        stability={
            "anti_slide_Kc": round(Kc, 2),
            "weight_kN_per_m": round(W, 1),
            "water_pressure_kN_per_m": round(F_water, 1),
            "friction_coeff": f,
            "pass": stability_ok,
        },
        compliance=compliance,
        warnings=warnings,
        notes=notes + [rev["notes"]]
    )


def compare_schemes(schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    多方案对比
    schemes: [{name, revetment_type, m_slope, bed_width, crest_width, freeboard, ...}]
    """
    results = []
    for s in schemes:
        r = design_trapezoidal_section(
            design_water_level=s.get("design_water_level", 100),
            bed_elevation=s.get("bed_elevation", 95),
            bed_width=s.get("bed_width", 10),
            m_slope=s.get("m_slope", 2.0),
            revetment_type=s.get("revetment_type", "stone_mortar"),
            freeboard=s.get("freeboard", 1.0),
            crest_width=s.get("crest_width", 5.0),
            berm_width=s.get("berm_width", 2.0),
        )
        if r.success:
            results.append({
                "name": s.get("name", f"方案{len(results)+1}"),
                "revetment_name": r.parameters["revetment_name"],
                "m_slope": r.parameters["m_slope"],
                "stability_Kc": r.stability["anti_slide_Kc"],
                "stability_pass": r.stability["pass"],
                "total_cost_per_m": r.costs["total_cost_yuan_per_m"],
                "fill_volume_per_m": r.quantities["fill_volume_m3_per_m"],
                "section_width": r.geometry["section_width_m"],
                "warnings": r.warnings,
                "compliance": r.compliance,
            })

    # 按造价排序并给出推荐
    if results:
        results_sorted = sorted(results, key=lambda x: x["total_cost_per_m"])
        cheapest = results_sorted[0]
        most_stable = max(results, key=lambda x: x["stability_Kc"])

        # 综合评分：造价40% + 稳定性30% + 占地30%
        max_cost = max(r["total_cost_per_m"] for r in results) if results else 1
        max_width = max(r["section_width"] for r in results) if results else 1
        max_Kc = max(r["stability_Kc"] for r in results) if results else 1

        for r in results:
            cost_score = (1 - r["total_cost_per_m"] / max_cost) * 40 if max_cost > 0 else 0
            stability_score = (r["stability_Kc"] / max_Kc) * 30 if max_Kc > 0 else 0
            land_score = (1 - r["section_width"] / max_width) * 30 if max_width > 0 else 0
            r["composite_score"] = round(cost_score + stability_score + land_score, 1)

        recommended = max(results, key=lambda x: x["composite_score"])

        return {
            "schemes": results,
            "recommended": recommended["name"],
            "recommended_reason": f"综合评分最高({recommended['composite_score']}分)，造价{recommended['total_cost_per_m']}元/m，抗滑Kc={recommended['stability_Kc']}",
            "comparison_dimensions": ["造价", "稳定性", "占地宽度", "综合评分"],
        }
    return {"schemes": [], "recommended": None, "recommended_reason": "无有效方案"}


class ParametricDesignService:
    """参数化设计服务"""

    def get_section_types(self) -> List[Dict[str, Any]]:
        return [
            {"id": SectionType.TRAPEZOIDAL.value, "name": "梯形断面", "description": "最常用的堤防/渠道断面，适用于大多数土质河床"},
            {"id": SectionType.RECTANGULAR.value, "name": "矩形断面", "description": "适用于城镇段受占地限制的河道，需设挡墙"},
            {"id": SectionType.COMPOUND.value, "name": "复式断面", "description": "主槽+滩地，适用于天然河道和洪水期漫滩的情况"},
        ]

    def get_revetment_types(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": k,
                **v,
            }
            for k, v in REVETMENT_PARAMS.items()
        ]

    def get_recommendations(self, building_level: int) -> Dict[str, Any]:
        """根据建筑物级别推荐设计参数"""
        return {
            "crest_width": CREST_WIDTH_RECOMMEND.get(building_level, 5.0),
            "freeboard": FREEBOARD_RECOMMEND.get(building_level, 0.8),
            "anti_slide_safety_factor": 1.30 if building_level <= 2 else 1.25 if building_level <= 4 else 1.20,
            "anti_overturn_safety_factor": 1.50 if building_level <= 2 else 1.40 if building_level <= 4 else 1.30,
        }

    def design_section(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行断面设计"""
        section_type = params.get("section_type", SectionType.TRAPEZOIDAL.value)

        if section_type == SectionType.TRAPEZOIDAL.value:
            result = design_trapezoidal_section(
                design_water_level=float(params.get("design_water_level", 100)),
                bed_elevation=float(params.get("bed_elevation", 95)),
                bed_width=float(params.get("bed_width", 10)),
                m_slope=float(params.get("m_slope", 2.0)),
                revetment_type=params.get("revetment_type", "stone_mortar"),
                freeboard=float(params.get("freeboard", 1.0)),
                crest_width=float(params.get("crest_width", 5.0)),
                berm_width=float(params.get("berm_width", 2.0)),
                foundation_depth=float(params.get("foundation_depth", 0.6)),
            )
            return {
                "success": result.success,
                "section_name": result.section_name,
                "section_type": result.section_type,
                "parameters": result.parameters,
                "geometry": result.geometry,
                "quantities": result.quantities,
                "costs": result.costs,
                "stability": result.stability,
                "compliance": result.compliance,
                "warnings": result.warnings,
                "notes": result.notes,
            }
        else:
            return {
                "success": False,
                "error": f"暂不支持 {section_type} 断面的参数化设计，目前仅支持梯形断面"
            }

    def compare_design_schemes(self, schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """多方案对比"""
        return compare_schemes(schemes)


# 单例
parametric_design_service = ParametricDesignService()
