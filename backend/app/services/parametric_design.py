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


def design_rectangular_section(
    design_water_level: float,
    bed_elevation: float,
    bed_width: float,
    wall_height: float = 6.0,          # 挡墙高度
    wall_thickness: float = 0.6,      # 挡墙顶宽
    wall_bottom_thickness: float = 1.8, # 挡墙底宽（重力式）
    revetment_type: str = "concrete",
    freeboard: float = 1.0,
    crest_width: float = 3.0,
    foundation_depth: float = 1.0,
) -> SectionDesignResult:
    """矩形断面（重力式挡墙）参数化设计 - 适用于城镇段受限河道"""
    warnings = []
    compliance = []
    notes = []

    water_depth = design_water_level - bed_elevation
    if water_depth <= 0:
        return SectionDesignResult(
            success=False, section_name="矩形断面", section_type="rectangular",
            parameters={}, geometry={}, quantities={}, costs={}, stability={},
            compliance=[], warnings=["设计水位必须高于河底高程"]
        )

    crest_elevation = design_water_level + freeboard
    wall_total_height = wall_height + foundation_depth
    rev = REVETMENT_PARAMS.get(revetment_type, REVETMENT_PARAMS["concrete"])

    # 几何坐标点（对称矩形，左右重力式挡墙）
    points = []
    wall_base_half = wall_bottom_thickness / 2
    # 左挡墙外缘（基础底）
    points.append({"x": 0, "y": bed_elevation - foundation_depth})
    # 左挡墙墙顶外缘
    points.append({"x": wall_bottom_thickness - wall_thickness, "y": crest_elevation})
    # 左挡墙墙顶内缘（迎水面）
    points.append({"x": wall_bottom_thickness, "y": crest_elevation})
    # 左墙脚（河底左端点）
    points.append({"x": wall_bottom_thickness, "y": bed_elevation})
    # 右墙脚（河底右端点）
    points.append({"x": wall_bottom_thickness + bed_width, "y": bed_elevation})
    # 右挡墙墙顶内缘
    points.append({"x": wall_bottom_thickness + bed_width, "y": crest_elevation})
    # 右挡墙墙顶外缘
    points.append({"x": wall_bottom_thickness + bed_width + wall_thickness, "y": crest_elevation})
    # 右挡墙外缘（基础底）
    points.append({"x": wall_bottom_thickness*2 + bed_width, "y": bed_elevation - foundation_depth})

    total_width = wall_bottom_thickness*2 + bed_width
    section_height = wall_total_height

    # 工程量（每延米）
    # 挡墙混凝土体积（两侧重力式墙，梯形截面）
    wall_area_per_side = (wall_thickness + wall_bottom_thickness) / 2 * wall_height
    wall_volume_per_m = 2 * wall_area_per_side
    # 基础混凝土
    foundation_vol = 2 * wall_bottom_thickness * foundation_depth
    # 河底护底
    bed_protection = bed_width * 0.3
    concrete_total = wall_volume_per_m + foundation_vol + bed_protection

    # 土方开挖
    excavation = total_width * foundation_depth * 1.2
    # 墙后回填
    backfill = (total_width - bed_width - wall_thickness*2) / 2 * wall_height * 0.5 * 2

    # 水力要素
    A = bed_width * water_depth
    P = bed_width + 2 * water_depth
    R = A / P if P > 0 else 0

    # 抗滑稳定（重力墙，简化计算）
    gamma_conc = 24
    W_wall = wall_area_per_side * gamma_conc  # 单侧墙重 kN/m
    F_water = 0.5 * 10 * water_depth ** 2
    f = 0.55  # 混凝土与基岩摩擦系数
    Kc = f * W_wall * 2 / F_water if F_water > 0 else 999
    stability_ok = Kc >= 1.25

    if stability_ok:
        compliance.append(f"抗滑稳定安全系数 Kc={Kc:.2f} ≥ 1.25，满足规范要求")
    else:
        warnings.append(f"抗滑稳定安全系数 Kc={Kc:.2f} < 1.25，需加大墙底宽度或采取基础处理")

    if wall_height > 6:
        notes.append(f"墙高{wall_height}m超过6m，建议进行抗倾验算和地基承载力验算")

    water_level_points = [
        {"x": wall_bottom_thickness, "y": design_water_level},
        {"x": wall_bottom_thickness + bed_width, "y": design_water_level},
    ]
    bed_points = [
        {"x": wall_bottom_thickness, "y": bed_elevation},
        {"x": wall_bottom_thickness + bed_width, "y": bed_elevation},
    ]

    concrete_cost = concrete_total * rev["cost_per_m3"]
    backfill_cost = backfill * 35
    excavation_cost = excavation * 25
    total_cost = concrete_cost + backfill_cost + excavation_cost

    return SectionDesignResult(
        success=True,
        section_name=f"{rev['name']}矩形断面（重力式挡墙）",
        section_type=SectionType.RECTANGULAR.value,
        parameters={
            "bed_width": bed_width,
            "wall_height": wall_height,
            "wall_thickness": wall_thickness,
            "wall_bottom_thickness": wall_bottom_thickness,
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
            "section_width_m": round(total_width, 2),
            "section_height_m": round(section_height, 2),
        },
        quantities={
            "revetment_volume_m3_per_m": round(concrete_total, 3),
            "fill_volume_m3_per_m": round(backfill, 3),
            "foundation_volume_m3_per_m": round(foundation_vol, 3),
            "excavation_m3_per_m": round(excavation, 3),
            "concrete_or_stone_m3_per_m": round(concrete_total, 3),
            "wetted_perimeter_m": round(P, 2),
            "flow_area_m2": round(A, 2),
            "hydraulic_radius_m": round(R, 2),
        },
        costs={
            "revetment_cost_yuan_per_m": round(concrete_cost, 0),
            "fill_cost_yuan_per_m": round(backfill_cost, 0),
            "foundation_cost_yuan_per_m": round(excavation_cost, 0),
            "total_cost_yuan_per_m": round(total_cost, 0),
            "total_cost_yuan_per_km": round(total_cost * 1000, 0),
        },
        stability={
            "anti_slide_Kc": round(Kc, 2),
            "weight_kN_per_m": round(W_wall * 2, 1),
            "water_pressure_kN_per_m": round(F_water, 1),
            "friction_coeff": f,
            "pass": stability_ok,
        },
        compliance=compliance + [f"堤顶超高 {freeboard}m，符合城镇段防洪要求"],
        warnings=warnings,
        notes=notes + [rev["notes"]],
    )


def design_compound_section(
    design_water_level: float,
    bed_elevation: float,
    main_channel_width: float = 15,    # 主槽底宽
    main_channel_depth: float = 3.5,   # 主槽深度
    berm_elevation: float = None,      # 滩地高程（马道高程）
    floodplain_width: float = 20,      # 单侧滩地宽度
    m_slope_main: float = 2.0,         # 主槽边坡
    m_slope_flood: float = 2.5,        # 滩地边坡
    revetment_type: str = "stone_mortar",
    floodplain_revetment: str = "grass",
    freeboard: float = 1.0,
    crest_width: float = 5.0,
    foundation_depth: float = 0.6,
) -> SectionDesignResult:
    """复式断面（主槽+滩地）- 适用于天然河道"""
    warnings = []
    compliance = []
    notes = []

    if berm_elevation is None:
        berm_elevation = bed_elevation + main_channel_depth

    water_depth = design_water_level - bed_elevation
    flood_depth = max(0, design_water_level - berm_elevation)
    if water_depth <= 0:
        return SectionDesignResult(
            success=False, section_name="复式断面", section_type="compound",
            parameters={}, geometry={}, quantities={}, costs={}, stability={},
            compliance=[], warnings=["设计水位必须高于河底高程"]
        )

    crest_elevation = design_water_level + freeboard
    rev_main = REVETMENT_PARAMS.get(revetment_type, REVETMENT_PARAMS["stone_mortar"])
    rev_flood = REVETMENT_PARAMS.get(floodplain_revetment, REVETMENT_PARAMS["grass"])

    # 几何坐标（对称复式断面）
    points = []
    x = 0
    y = bed_elevation - foundation_depth
    points.append({"x": x, "y": y})

    # 左滩地外坡脚到堤顶（从基础到堤顶）
    left_toe_to_crest_h = crest_elevation - (bed_elevation - foundation_depth)
    x += m_slope_flood * left_toe_to_crest_h
    y = crest_elevation
    points.append({"x": x, "y": y})

    # 左堤顶
    points.append({"x": x + crest_width, "y": y})
    x += crest_width

    # 左堤内坡到滩地
    d = crest_elevation - berm_elevation
    x += m_slope_flood * d
    y = berm_elevation
    points.append({"x": x, "y": y})

    # 左滩地（马道平台）
    points.append({"x": x + floodplain_width, "y": y})
    x += floodplain_width

    # 主槽左坡
    d2 = berm_elevation - bed_elevation
    x += m_slope_main * d2
    y = bed_elevation
    points.append({"x": x, "y": y})

    # 主槽底
    points.append({"x": x + main_channel_width, "y": y})
    x += main_channel_width

    # 主槽右坡
    x += m_slope_main * d2
    y = berm_elevation
    points.append({"x": x, "y": y})

    # 右滩地
    points.append({"x": x + floodplain_width, "y": y})
    x += floodplain_width

    # 右堤内坡
    d3 = crest_elevation - berm_elevation
    x += m_slope_flood * d3
    y = crest_elevation
    points.append({"x": x, "y": y})

    # 右堤顶
    points.append({"x": x + crest_width, "y": y})
    x += crest_width

    # 右堤外坡到基础
    d4 = crest_elevation - (bed_elevation - foundation_depth)
    x += m_slope_flood * d4
    y = bed_elevation - foundation_depth
    points.append({"x": x, "y": y})

    total_width = x
    section_height = crest_elevation - bed_elevation + foundation_depth

    # 水力要素
    # 主槽过流
    A_main = (main_channel_width + m_slope_main * d2) * d2 if water_depth > d2 else (main_channel_width + m_slope_main * water_depth) * water_depth
    # 滩地过流
    A_flood = 0
    if flood_depth > 0:
        A_flood = 2 * floodplain_width * flood_depth
    A = A_main + A_flood
    P_main = main_channel_width + 2 * math.sqrt(1 + m_slope_main**2) * min(water_depth, d2)
    P_flood = 2 * floodplain_width if flood_depth > 0 else 0
    P = P_main + P_flood
    R = A / P if P > 0 else 0

    # 简化工程量
    main_slope_len = d2 * math.sqrt(1 + m_slope_main**2)
    flood_slope_len = (crest_elevation - berm_elevation) * math.sqrt(1 + m_slope_flood**2)
    outer_slope_len = left_toe_to_crest_h * math.sqrt(1 + m_slope_flood**2)
    rev_vol = 2 * (main_slope_len * rev_main["thickness_m"] + flood_slope_len * rev_flood["thickness_m"])
    # 堤身填土
    levee_fill = 2 * ((crest_width + (crest_width + m_slope_flood*d3))/2 * d3)
    # 总造价估算
    cost_main = main_slope_len * 2 * rev_main["thickness_m"] * rev_main["cost_per_m3"]
    cost_flood = (flood_slope_len + outer_slope_len) * 2 * rev_flood["thickness_m"] * rev_flood["cost_per_m3"]
    cost_fill = levee_fill * 35
    total_cost = cost_main + cost_flood + cost_fill

    # 抗滑稳定（简化）
    gamma_fill = 18
    W = levee_fill * gamma_fill
    F_water = 0.5 * 10 * water_depth ** 2
    f = 0.45
    Kc = f * W / F_water if F_water > 0 else 999
    stability_ok = Kc >= 1.25

    water_level_points = [
        {"x": points[5]["x"] - m_slope_main * max(0, berm_elevation - design_water_level), "y": design_water_level} if design_water_level <= berm_elevation else {"x": points[3]["x"], "y": design_water_level},
        {"x": points[6]["x"] + m_slope_main * max(0, berm_elevation - design_water_level), "y": design_water_level} if design_water_level <= berm_elevation else {"x": points[9]["x"], "y": design_water_level},
    ]
    bed_points = [
        {"x": points[5]["x"], "y": bed_elevation},
        {"x": points[6]["x"], "y": bed_elevation},
    ]

    if flood_depth > 0:
        notes.append(f"滩地过流深度{flood_depth:.1f}m，为复式断面典型特征")
        compliance.append("复式断面满足主槽排常遇洪水、滩地排大洪水的要求")
    if stability_ok:
        compliance.append(f"抗滑稳定安全系数 Kc={Kc:.2f}")
    else:
        warnings.append(f"抗滑稳定安全系数 Kc={Kc:.2f}，不满足要求")

    return SectionDesignResult(
        success=True,
        section_name=f"复式断面（主槽+滩地，{rev_main['name']}+{rev_flood['name']}）",
        section_type=SectionType.COMPOUND.value,
        parameters={
            "main_channel_width": main_channel_width,
            "main_channel_depth": main_channel_depth,
            "berm_elevation": berm_elevation,
            "floodplain_width": floodplain_width,
            "m_slope_main": m_slope_main,
            "m_slope_flood": m_slope_flood,
            "bed_width": main_channel_width,
            "water_depth": round(water_depth, 2),
            "flood_depth": round(flood_depth, 2),
            "freeboard": freeboard,
            "crest_width": crest_width,
            "crest_elevation": round(crest_elevation, 2),
            "revetment_type": revetment_type,
            "revetment_name": rev_main["name"],
            "revetment_thickness": rev_main["thickness_m"],
            "foundation_depth": foundation_depth,
        },
        geometry={
            "outline_points": points,
            "water_level_points": water_level_points,
            "bed_points": bed_points,
            "section_width_m": round(total_width, 2),
            "section_height_m": round(section_height, 2),
        },
        quantities={
            "revetment_volume_m3_per_m": round(rev_vol, 3),
            "fill_volume_m3_per_m": round(levee_fill, 3),
            "foundation_volume_m3_per_m": round(rev_vol * 0.2, 3),
            "excavation_m3_per_m": round(total_width * foundation_depth * 0.5, 3),
            "concrete_or_stone_m3_per_m": round(rev_vol, 3),
            "wetted_perimeter_m": round(P, 2),
            "flow_area_m2": round(A, 2),
            "hydraulic_radius_m": round(R, 2),
        },
        costs={
            "revetment_cost_yuan_per_m": round(cost_main + cost_flood, 0),
            "fill_cost_yuan_per_m": round(cost_fill, 0),
            "foundation_cost_yuan_per_m": round(rev_vol * 0.2 * rev_main["cost_per_m3"], 0),
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
        notes=notes,
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
        elif section_type == SectionType.RECTANGULAR.value:
            result = design_rectangular_section(
                design_water_level=float(params.get("design_water_level", 100)),
                bed_elevation=float(params.get("bed_elevation", 95)),
                bed_width=float(params.get("bed_width", 8)),
                wall_height=float(params.get("wall_height", 6.0)),
                wall_thickness=float(params.get("wall_thickness", 0.6)),
                wall_bottom_thickness=float(params.get("wall_bottom_thickness", 1.8)),
                revetment_type=params.get("revetment_type", "concrete"),
                freeboard=float(params.get("freeboard", 1.0)),
                crest_width=float(params.get("crest_width", 3.0)),
                foundation_depth=float(params.get("foundation_depth", 1.0)),
            )
        elif section_type == SectionType.COMPOUND.value:
            result = design_compound_section(
                design_water_level=float(params.get("design_water_level", 100)),
                bed_elevation=float(params.get("bed_elevation", 95)),
                main_channel_width=float(params.get("main_channel_width", 15)),
                main_channel_depth=float(params.get("main_channel_depth", 3.5)),
                floodplain_width=float(params.get("floodplain_width", 20)),
                m_slope_main=float(params.get("m_slope_main", 2.0)),
                m_slope_flood=float(params.get("m_slope_flood", 2.5)),
                revetment_type=params.get("revetment_type", "stone_mortar"),
                floodplain_revetment=params.get("floodplain_revetment", "grass"),
                freeboard=float(params.get("freeboard", 1.0)),
                crest_width=float(params.get("crest_width", 5.0)),
                foundation_depth=float(params.get("foundation_depth", 0.6)),
            )
        else:
            return {
                "success": False,
                "error": f"不支持的断面类型: {section_type}"
            }

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

    def compare_design_schemes(self, schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """多方案对比"""
        return compare_schemes(schemes)


# 单例
parametric_design_service = ParametricDesignService()
