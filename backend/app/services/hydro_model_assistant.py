"""
水文模型辅助服务
================
提供 SWMM (Storm Water Management Model) 等水文模型的：
1. 参数推荐与inp输入文件生成
2. 模型输出报告(.rpt)解析
3. 结果可视化数据生成
4. 设计暴雨生成（芝加哥雨型、Huff雨型等）

注意：不直接运行模型（需要外部SWMM软件），而是帮助设计人员准备输入、解析输出。
"""
import re
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import random


@dataclass
class ModelResult:
    """模型辅助结果通用结构"""
    success: bool
    model_type: str
    operation: str
    data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


# ==================== 设计暴雨生成 ====================

# 中国暴雨强度公式参数（q 单位：L/(s·ha)）
# 公式：q = A1 * (1 + C * lgP) / (t + b)^n
# 参数来源：各城市暴雨强度公式（修编版），A1 值已对应 q 的单位
RAINFALL_INTENSITY_PARAMS = {
    "成都": {"A1": 2006, "C": 0.725, "b": 12.8, "n": 0.801},
    "乐山": {"A1": 1867, "C": 0.680, "b": 11.5, "n": 0.780},
    "绵阳": {"A1": 1809, "C": 0.650, "b": 10.8, "n": 0.760},
    "德阳": {"A1": 1750, "C": 0.640, "b": 10.2, "n": 0.755},
    "眉山": {"A1": 1817, "C": 0.660, "b": 11.0, "n": 0.770},
    "自贡": {"A1": 1917, "C": 0.690, "b": 12.0, "n": 0.785},
    "内江": {"A1": 1834, "C": 0.670, "b": 11.2, "n": 0.775},
    "遂宁": {"A1": 1784, "C": 0.655, "b": 10.5, "n": 0.765},
    "广元": {"A1": 1700, "C": 0.620, "b": 9.8,  "n": 0.745},
    "雅安": {"A1": 2250, "C": 0.780, "b": 14.0, "n": 0.820},
    "重庆": {"A1": 2418, "C": 0.800, "b": 15.0, "n": 0.830},
    "北京": {"A1": 2001, "C": 0.811, "b": 8.0,  "n": 0.711},
    "上海": {"A1": 5544, "C": 0.820, "b": 10.0, "n": 0.820},
    "广州": {"A1": 2424, "C": 0.750, "b": 14.0, "n": 0.750},
}


def rainfall_intensity(city: str, return_period: float, duration_min: float) -> float:
    """
    暴雨强度计算（中国城市暴雨强度公式）
    q = (A1 * (1 + C * lgP)) / (t + b)^n
    单位: L/(s·ha)
    P: 重现期(年), t: 降雨历时(min)
    """
    params = RAINFALL_INTENSITY_PARAMS.get(city)
    if not params:
        raise ValueError(f"未配置城市 {city} 的暴雨强度公式参数")
    A1, C, b, n = params["A1"], params["C"], params["b"], params["n"]
    q = (A1 * (1 + C * math.log10(return_period))) / ((duration_min + b) ** n)
    return q  # L/(s·ha)


def _instantaneous_intensity(city: str, return_period: float, t_min: float) -> float:
    """
    瞬时暴雨强度（芝加哥雨型用）
    i(t) = d/dt [ (A/(t+b)^n) * t ] 的微分
    即瞬时强度 = A * (1-n) / (t+b)^(n+1) * b + A/(t+b)^n （简化用A*(1-n*t/(t+b))/(t+b)^n）
    标准芝加哥法瞬时强度：
      i(t) = A * [ (1-n) + n*b/(t+b) ] / (t+b)^n
    """
    params = RAINFALL_INTENSITY_PARAMS.get(city)
    A1, C, b, n = params["A1"], params["C"], params["b"], params["n"]
    A = A1 * (1 + C * math.log10(return_period))
    t = max(t_min, 0.1)
    i = A * ((1 - n) + n * b / (t + b)) / ((t + b) ** n)
    return i  # L/(s·ha)


def generate_chicago_hyetograph(
    city: str,
    return_period: float = 20,
    duration_min: float = 120,
    timestep_min: float = 5,
    r: float = 0.4,
) -> Dict[str, Any]:
    """
    芝加哥雨型生成器（Keifer & Chu, 1957）
    r: 雨峰系数(0~1)，通常取0.3~0.5
    返回时间序列(分钟)和雨强序列(mm/h)

    采用时段平均强度计算：
    - 对每个时间步，计算该时段的累积雨量差除以时段长度
    - 累积雨量公式 H(t) = A * t / (t + b)^n  （由 q = dH/dt 的积分形式）
    """
    if city not in RAINFALL_INTENSITY_PARAMS:
        raise ValueError(f"不支持城市 {city}")

    params = RAINFALL_INTENSITY_PARAMS[city]
    A1, C, b, n = params["A1"], params["C"], params["b"], params["n"]
    A = A1 * (1 + C * math.log10(return_period))

    steps = int(duration_min / timestep_min)
    peak_step = int(steps * r)
    peak_time_min = peak_step * timestep_min

    def instantaneous_intensity_prepeak(tb: float) -> float:
        """峰前瞬时雨强 (L/(s·ha))，tb为距雨峰的时间(min)，除以r得到等效历时"""
        if tb <= 0:
            tb = 0.01
        t_eq = tb / r
        # 对累积雨量 D(t) = A*t/(t+b)^n 求导得瞬时强度
        # dD/dt = A*[(1-n)*t + b]/(t+b)^(n+1)，然后乘上 dt_eq/dt_actual = 1/r
        return A * ((1 - n) * t_eq + b) / ((t_eq + b) ** (n + 1)) / r

    def instantaneous_intensity_postpeak(ta: float) -> float:
        """峰后瞬时雨强 (L/(s·ha))，ta为距雨峰时间(min)"""
        if ta <= 0:
            ta = 0.01
        t_eq = ta / (1 - r)
        return A * ((1 - n) * t_eq + b) / ((t_eq + b) ** (n + 1)) / (1 - r)

    times = []
    intensities_mm_h = []

    # 用细分数值积分求每个时段的平均雨强
    sub_steps = 50  # 每个时段分50个子步求平均
    for i in range(steps):
        t_start = i * timestep_min
        t_end = t_start + timestep_min
        times.append(round(t_start, 1))

        # 数值积分：在时段内取 sub_steps 个点求平均
        dt_sub = timestep_min / sub_steps
        sum_i = 0.0
        for k in range(sub_steps):
            t_mid = t_start + (k + 0.5) * dt_sub
            if t_mid < peak_time_min:
                tb = peak_time_min - t_mid
                i_q = instantaneous_intensity_prepeak(tb)
            elif t_mid > peak_time_min:
                ta = t_mid - peak_time_min
                i_q = instantaneous_intensity_postpeak(ta)
            else:
                # 正好在峰上（概率极小），取前后平均
                i_q = (instantaneous_intensity_prepeak(0.01) + instantaneous_intensity_postpeak(0.01)) / 2
            sum_i += i_q

        avg_q = sum_i / sub_steps  # L/(s·ha)
        i_mm_h = avg_q * 0.36     # 转换为 mm/h
        intensities_mm_h.append(round(max(0, i_mm_h), 2))

    # 归一化使总降雨量与暴雨强度公式一致（考虑到离散化误差）
    q_avg = rainfall_intensity(city, return_period, duration_min)
    total_depth_mm = q_avg * 0.36 * duration_min / 60
    current_total = sum(intensities_mm_h) * timestep_min / 60
    if current_total > 0:
        scale = total_depth_mm / current_total
        intensities_mm_h = [round(i * scale, 2) for i in intensities_mm_h]

    peak_intensity = max(intensities_mm_h)
    peak_time = times[intensities_mm_h.index(peak_intensity)]

    return {
        "city": city,
        "return_period": return_period,
        "duration_min": duration_min,
        "timestep_min": timestep_min,
        "r": r,
        "total_rainfall_mm": round(sum(intensities_mm_h) * timestep_min / 60, 2),
        "avg_intensity_mm_h": round(q_avg * 0.36, 2),
        "peak_intensity_mm_h": round(peak_intensity, 2),
        "peak_intensity_ratio": round(peak_intensity / (q_avg * 0.36), 2) if q_avg > 0 else 0,
        "peak_time_min": peak_time,
        "times_min": times,
        "intensities_mm_h": intensities_mm_h,
        "formula": f"q = {A1}×(1+{C}×lgP)/(t+{b})^{n}  [L/(s·ha)]",
    }


# ==================== SWMM INP 文件生成 ====================

# SWMM 子汇水区参数推荐表（按用地类型）
SUBCATCHMENT_DEFAULTS = {
    "residential": {  # 居住区
        "n_imperv": 0.01, "n_perv": 0.15,
        "s_imperv": 2.5, "s_perv": 5.0,
        "pct_zero": 25, "pct_imperv": 60,
        "name": "居住区"
    },
    "commercial": {  # 商业区
        "n_imperv": 0.012, "n_perv": 0.12,
        "s_imperv": 2.0, "s_perv": 4.0,
        "pct_zero": 40, "pct_imperv": 85,
        "name": "商业区"
    },
    "industrial": {  # 工业区
        "n_imperv": 0.013, "n_perv": 0.10,
        "s_imperv": 2.0, "s_perv": 3.5,
        "pct_zero": 30, "pct_imperv": 75,
        "name": "工业区"
    },
    "green_space": {  # 绿地/公园
        "n_imperv": 0.015, "n_perv": 0.25,
        "s_imperv": 3.0, "s_perv": 8.0,
        "pct_zero": 10, "pct_imperv": 10,
        "name": "绿地公园"
    },
    "road": {  # 道路广场
        "n_imperv": 0.011, "n_perv": 0.15,
        "s_imperv": 1.5, "s_perv": 3.0,
        "pct_zero": 60, "pct_imperv": 95,
        "name": "道路广场"
    },
    "water": {  # 水体
        "n_imperv": 0.01, "n_perv": 0.05,
        "s_imperv": 0.5, "s_perv": 1.0,
        "pct_zero": 100, "pct_imperv": 100,
        "name": "水体"
    },
    "agricultural": {  # 农田
        "n_imperv": 0.015, "n_perv": 0.20,
        "s_imperv": 3.0, "s_perv": 6.0,
        "pct_zero": 5, "pct_imperv": 5,
        "name": "农田"
    },
}

# SWMM 管道参数推荐（按管材）
CONDUIT_DEFAULTS = {
    "concrete": {"n": 0.013, "name": "混凝土管"},
    "pvc": {"n": 0.010, "name": "PVC管"},
    "hdpe": {"n": 0.010, "name": "HDPE双壁波纹管"},
    "brick": {"n": 0.015, "name": "砖砌方沟"},
    "stone": {"n": 0.018, "name": "浆砌石渠道"},
    "earth": {"n": 0.025, "name": "土渠"},
}


def generate_swmm_inp(
    project_name: str,
    subcatchments: List[Dict[str, Any]],
    junctions: List[Dict[str, Any]],
    conduits: List[Dict[str, Any]],
    outfalls: List[Dict[str, Any]],
    rain_gauge: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    生成 SWMM .inp 输入文件内容
    subcatchments: [{name, land_use, area_ha, width_m, slope_pct, outlet, ...}]
    junctions: [{name, invert_elev_m, max_depth_m, ...}]
    conduits: [{name, from_node, to_node, length_m, diameter_m, material, ...}]
    outfalls: [{name, invert_elev_m, type(Free/Normal/Fixed), ...}]
    rain_gauge: {format, interval, ...}
    """
    warnings = []
    notes = []

    if rain_gauge is None:
        rain_gauge = {"format": "INTENSITY", "interval": "00:05", "name": "RG1"}

    lines = []
    lines.append("[TITLE]")
    lines.append(f";;Project Title")
    lines.append(f"{project_name}")
    lines.append("")

    # Options
    lines.append("[OPTIONS]")
    lines.append("FLOW_UNITS           CMS")
    lines.append("INFILTRATION         HORTON")
    lines.append("FLOW_ROUTING         KINWAVE")
    lines.append("START_DATE           07/01/2025")
    lines.append("START_TIME           00:00:00")
    lines.append("END_DATE             07/01/2025")
    lines.append("END_TIME             04:00:00")
    lines.append("REPORT_STEP          00:05:00")
    lines.append("WET_STEP             00:05:00")
    lines.append("DRY_STEP             00:30:00")
    lines.append("ROUTING_STEP         00:00:30")
    lines.append("ALLOW_PONDING        NO")
    lines.append("SKIP_STEADY_STATE    NO")
    lines.append("")

    # Raingages
    lines.append("[RAINGAGES]")
    lines.append(";;Name           Format    Interval  SCF    Source    File/Table")
    lines.append(f"{rain_gauge.get('name','RG1'):<16} INTENSITY {rain_gauge.get('interval','00:05'):<8} 1.0    TIMESERIES RAIN_TS")
    lines.append("")

    # Subcatchments
    lines.append("[SUBCATCHMENTS]")
    lines.append(";;Name           Rain Gage        Outlet           Area     %Imperv  Width    %Slope  CurbLen  SnowPack")
    for sc in subcatchments:
        land_use = sc.get("land_use", "residential")
        defaults = SUBCATCHMENT_DEFAULTS.get(land_use, SUBCATCHMENT_DEFAULTS["residential"])
        name = sc["name"]
        rg = sc.get("rain_gauge", rain_gauge.get("name", "RG1"))
        outlet = sc.get("outlet", "")
        area = sc.get("area_ha", 1.0)
        pct_imperv = sc.get("pct_imperv", defaults["pct_imperv"])
        width = sc.get("width_m", math.sqrt(area * 10000) * 0.5)
        slope = sc.get("slope_pct", defaults["s_perv"]/2)
        curb_len = sc.get("curb_len", 0)
        lines.append(f"{name:<16} {rg:<16} {outlet:<16} {area:<8.3f} {pct_imperv:<8.1f} {width:<8.1f} {slope:<8.2f} {curb_len:<8.1f}")
        if land_use not in SUBCATCHMENT_DEFAULTS:
            warnings.append(f"子汇水区 {name} 的用地类型 {land_use} 未识别，使用居住区默认参数")
    lines.append("")

    # Subareas
    lines.append("[SUBAREAS]")
    lines.append(";;Subcatchment   N-Imperv  N-Perv    S-Imperv  S-Perv    PctZero   RouteTo    PctRouted")
    for sc in subcatchments:
        land_use = sc.get("land_use", "residential")
        defaults = SUBCATCHMENT_DEFAULTS.get(land_use, SUBCATCHMENT_DEFAULTS["residential"])
        name = sc["name"]
        n_imp = sc.get("n_imperv", defaults["n_imperv"])
        n_perv = sc.get("n_perv", defaults["n_perv"])
        s_imp = sc.get("s_imperv", defaults["s_imperv"])
        s_perv = sc.get("s_perv", defaults["s_perv"])
        pct_zero = sc.get("pct_zero", defaults["pct_zero"])
        lines.append(f"{name:<16} {n_imp:<9.4f} {n_perv:<9.4f} {s_imp:<9.2f} {s_perv:<9.2f} {pct_zero:<9.1f} OUTLET     100")
    lines.append("")

    # Infiltration (Horton)
    lines.append("[INFILTRATION]")
    lines.append(";;Subcatchment   MaxRate   MinRate   Decay     DryTime   MaxInfil")
    for sc in subcatchments:
        name = sc["name"]
        # Horton参数默认值（按土壤类型）
        soil = sc.get("soil_type", "loam")
        horton_params = {
            "clay":     (30,  2, 2),
            "loam":     (75,  5, 4),
            "sand":     (120, 10, 6),
            "gravel":   (150, 15, 8),
        }
        max_r, min_r, decay = horton_params.get(soil, horton_params["loam"])
        lines.append(f"{name:<16} {max_r:<9.2f} {min_r:<9.3f} {decay:<9.2f} 7         0")
    lines.append("")

    # Junctions
    lines.append("[JUNCTIONS]")
    lines.append(";;Name           Elevation  MaxDepth   InitDepth  SurDepth   Aponded")
    for j in junctions:
        name = j["name"]
        elev = j.get("invert_elev_m", 0)
        max_d = j.get("max_depth_m", 2.5)
        init_d = j.get("init_depth_m", 0)
        sur_d = j.get("sur_depth_m", 0)
        apond = j.get("aponded", 0)
        lines.append(f"{name:<16} {elev:<10.3f} {max_d:<10.2f} {init_d:<10.2f} {sur_d:<10.2f} {apond:<10.1f}")
    lines.append("")

    # Outfalls
    lines.append("[OUTFALLS]")
    lines.append(";;Name           Elevation  Type       Stage Data       Gated    RouteTo")
    for o in outfalls:
        name = o["name"]
        elev = o.get("invert_elev_m", 0)
        otype = o.get("type", "FREE")
        lines.append(f"{name:<16} {elev:<10.3f} {otype:<10}                 NO")
    lines.append("")

    # Conduits
    lines.append("[CONDUITS]")
    lines.append(";;Name           From Node        To Node          Length     Roughness  InOffset   OutOffset  InitFlow   MaxFlow")
    for c in conduits:
        name = c["name"]
        fnode = c["from_node"]
        tnode = c["to_node"]
        length = c.get("length_m", 50)
        material = c.get("material", "concrete")
        n = CONDUIT_DEFAULTS.get(material, CONDUIT_DEFAULTS["concrete"])["n"]
        n = c.get("mannings_n", n)
        in_off = c.get("in_offset_m", 0)
        out_off = c.get("out_offset_m", 0)
        init_flow = c.get("init_flow", 0)
        max_flow = c.get("max_flow", 0)
        lines.append(f"{name:<16} {fnode:<16} {tnode:<16} {length:<10.1f} {n:<10.4f} {in_off:<10.3f} {out_off:<10.3f} {init_flow:<10.3f} {max_flow:<10.1f}")
        if material not in CONDUIT_DEFAULTS:
            warnings.append(f"管段 {name} 的管材 {material} 未识别，使用混凝土管默认糙率")
    lines.append("")

    # Cross Sections
    lines.append("[XSECTIONS]")
    lines.append(";;Link           Shape        Geom1      Geom2      Geom3      Geom4      Barrels    Culvert")
    for c in conduits:
        name = c["name"]
        shape = c.get("shape", "CIRCULAR")
        geom1 = c.get("diameter_m", 0.8)
        if shape == "RECT_CLOSED":
            geom1 = c.get("width_m", 1.0)
            geom2 = c.get("height_m", 1.0)
            lines.append(f"{name:<16} {shape:<12} {geom1:<10.3f} {geom2:<10.3f} 0          0          1")
        else:
            lines.append(f"{name:<16} {shape:<12} {geom1:<10.3f} 0          0          0          1")
    lines.append("")

    # Timeseries placeholder
    lines.append("[TIMESERIES]")
    lines.append(";;Name           Date       Time       Value")
    lines.append("RAIN_TS         FILE       \"rainfall.dat\"")
    lines.append("")

    # Report
    lines.append("[REPORT]")
    lines.append("INPUT      YES")
    lines.append("CONTROLS   NO")
    lines.append("SUBCATCHMENTS ALL")
    lines.append("NODES      ALL")
    lines.append("LINKS      ALL")
    lines.append("")

    inp_content = "\n".join(lines)

    notes.append(f"生成了 {len(subcatchments)} 个子汇水区")
    notes.append(f"生成了 {len(junctions)} 个节点")
    notes.append(f"生成了 {len(conduits)} 条管段")
    notes.append(f"生成了 {len(outfalls)} 个排放口")
    notes.append("降雨数据请在 RAIN_TS 时间序列中填入实际数据（可使用芝加哥雨型生成器）")

    return {
        "inp_content": inp_content,
        "project_name": project_name,
        "element_counts": {
            "subcatchments": len(subcatchments),
            "junctions": len(junctions),
            "conduits": len(conduits),
            "outfalls": len(outfalls),
        },
        "warnings": warnings,
        "notes": notes,
        "land_use_options": [{"key": k, "name": v["name"], "pct_imperv": v["pct_imperv"]} for k, v in SUBCATCHMENT_DEFAULTS.items()],
        "conduit_material_options": [{"key": k, "name": v["name"], "n": v["n"]} for k, v in CONDUIT_DEFAULTS.items()],
        "supported_cities": list(RAINFALL_INTENSITY_PARAMS.keys()),
    }


# ==================== SWMM RPT 报告解析 ====================

def parse_swmm_rpt(rpt_content: str) -> Dict[str, Any]:
    """
    解析 SWMM .rpt 输出报告文件
    提取：径流连续性、节点超载、管段超载、子汇水区径流总结等关键信息
    """
    warnings = []
    errors = []
    result = {
        "summary": {},
        "continuity": {},
        "subcatchment_results": [],
        "node_flooding": [],
        "conduit_surcharge": [],
        "warnings": warnings,
        "errors": errors,
    }

    lines = rpt_content.split("\n")

    # 解析径流连续性误差
    continuity_section = False
    for i, line in enumerate(lines):
        if "Runoff Quantity Continuity" in line:
            continuity_section = True
            continue
        if continuity_section:
            if ".........." in line:
                continue
            if line.strip().startswith("Total") and "Runoff" not in line:
                # 解析
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        result["continuity"]["total_precip"] = float(parts[-3] if len(parts) > 3 else parts[-1])
                    except ValueError:
                        pass
            if "Continuity Error" in line:
                m = re.search(r"([\d\.\-]+)\s*%", line)
                if m:
                    err_pct = float(m.group(1))
                    result["continuity"]["runoff_error_pct"] = err_pct
                    if abs(err_pct) > 5:
                        warnings.append(f"径流连续性误差 {err_pct:.1f}%，超过5%，建议检查时间步长")
                continuity_section = False

    # 解析流量演算连续性误差
    routing_section = False
    for i, line in enumerate(lines):
        if "Flow Routing Continuity" in line:
            routing_section = True
            continue
        if routing_section:
            if "Continuity Error" in line:
                m = re.search(r"([\d\.\-]+)\s*%", line)
                if m:
                    err_pct = float(m.group(1))
                    result["continuity"]["routing_error_pct"] = err_pct
                    if abs(err_pct) > 5:
                        warnings.append(f"流量演算连续性误差 {err_pct:.1f}%，超过5%，建议减小演算步长")
                routing_section = False

    # 解析子汇水区径流总结
    sub_section = False
    header_found = False
    for i, line in enumerate(lines):
        if "Subcatchment Runoff Summary" in line:
            sub_section = True
            continue
        if sub_section:
            if "---------" in line:
                header_found = True
                continue
            if header_found and line.strip() and not line.startswith(" ") and "===" not in line:
                parts = line.split()
                if len(parts) >= 8:
                    try:
                        sc = {
                            "name": parts[0],
                            "total_precip_mm": _safe_float(parts[1]),
                            "total_runon_mm": _safe_float(parts[2]),
                            "total_evap_mm": _safe_float(parts[3]),
                            "total_infil_mm": _safe_float(parts[4]),
                            "runoff_mm": _safe_float(parts[5]),
                            "peak_runoff_lps_ha": _safe_float(parts[6]),
                            "runoff_coeff": _safe_float(parts[7]) if len(parts) > 7 else None,
                        }
                        result["subcatchment_results"].append(sc)
                    except (ValueError, IndexError):
                        pass
            if "===" in line or (header_found and not line.strip()):
                if result["subcatchment_results"]:
                    sub_section = False

    # 解析节点积水
    flood_section = False
    header_found = False
    for i, line in enumerate(lines):
        if "Node Flooding Summary" in line or "Junction Flooding Summary" in line:
            flood_section = True
            continue
        if flood_section:
            if "---------" in line:
                header_found = True
                continue
            if header_found and line.strip() and not line.startswith(" "):
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        flood = {
                            "node": parts[0],
                            "hours_flooded": _safe_float(parts[1]),
                            "max_rate_lps": _safe_float(parts[2]),
                            "max_depth_m": _safe_float(parts[-3]) if len(parts) > 5 else None,
                            "time_peak": parts[-2] if len(parts) > 2 else "",
                        }
                        result["node_flooding"].append(flood)
                    except (ValueError, IndexError):
                        pass
            if "===" in line or (header_found and not line.strip()):
                if result["node_flooding"]:
                    flood_section = False

    # 解析管段超载
    sur_section = False
    header_found = False
    for i, line in enumerate(lines):
        if "Conduit Surcharge Summary" in line or "Link Surcharge Summary" in line:
            sur_section = True
            continue
        if sur_section:
            if "---------" in line:
                header_found = True
                continue
            if header_found and line.strip() and not line.startswith(" "):
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        surcharge = {
                            "conduit": parts[0],
                            "hours_surcharged": _safe_float(parts[-4]) if len(parts) > 4 else 0,
                            "hours_full_flow": _safe_float(parts[-3]) if len(parts) > 3 else 0,
                            "hours_upstream_full": _safe_float(parts[-2]) if len(parts) > 2 else 0,
                            "capacity_limited": parts[-1] if len(parts) > 1 else "",
                        }
                        result["conduit_surcharge"].append(surcharge)
                    except (ValueError, IndexError):
                        pass
            if "===" in line or (header_found and not line.strip()):
                if result["conduit_surcharge"]:
                    sur_section = False

    # 汇总
    result["summary"] = {
        "subcatchment_count": len(result["subcatchment_results"]),
        "flooding_node_count": len(result["node_flooding"]),
        "surcharged_conduit_count": len(result["conduit_surcharge"]),
        "max_flooding_nodes": sorted(result["node_flooding"], key=lambda x: x.get("hours_flooded", 0), reverse=True)[:5],
        "max_surcharge_conduits": sorted(result["conduit_surcharge"], key=lambda x: x.get("hours_surcharged", 0), reverse=True)[:5],
    }

    # 自动诊断
    if result["continuity"].get("runoff_error_pct") and abs(result["continuity"]["runoff_error_pct"]) > 10:
        errors.append(f"径流连续性误差{result['continuity']['runoff_error_pct']:.1f}%过大，结果不可信，请减小WET_STEP")
    if result["summary"]["flooding_node_count"] > 0:
        warnings.append(f"存在 {result['summary']['flooding_node_count']} 个积水节点，建议检查管径或增设调蓄设施")
    if result["summary"]["surcharged_conduit_count"] > 0:
        warnings.append(f"存在 {result['summary']['surcharged_conduit_count']} 条超载管段，建议复核管径")

    return result


def _safe_float(s: str) -> Optional[float]:
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# ==================== 主服务类 ====================

class HydroModelAssistant:
    """水文模型辅助服务"""

    def get_supported_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "swmm",
                "name": "SWMM 暴雨管理模型",
                "description": "EPA SWMM 城市雨洪模型，用于排水管网、海绵城市、内涝模拟",
                "features": ["芝加哥雨型生成", "INP输入文件生成", "RPT报告解析", "结果诊断"],
                "version": "5.2",
            },
            {
                "id": "rational",
                "name": "推理公式法",
                "description": "小流域暴雨洪水推理公式计算（Q = 0.278ψiF）",
                "features": ["设计洪水计算", "洪峰流量", "汇流时间"],
                "version": "-",
            },
            {
                "id": "hechms",
                "name": "HEC-HMS 概念模型",
                "description": "HEC-HMS 流域水文模型辅助参数准备",
                "features": ["CN值推荐", "单位线参数", "输入文件模板"],
                "version": "4.11",
            },
        ]

    def generate_rainfall(self, params: Dict[str, Any]) -> ModelResult:
        """生成设计暴雨"""
        city = params.get("city", "成都")
        return_period = float(params.get("return_period", 20))
        duration = float(params.get("duration_min", 120))
        timestep = float(params.get("timestep_min", 5))
        r = float(params.get("r_factor", 0.4))

        if city not in RAINFALL_INTENSITY_PARAMS:
            return ModelResult(
                success=False, model_type="rainfall", operation="generate",
                errors=[f"不支持城市 {city}，当前支持：{', '.join(RAINFALL_INTENSITY_PARAMS.keys())}"]
            )

        try:
            data = generate_chicago_hyetograph(city, return_period, duration, timestep, r)
            notes = [
                f"采用芝加哥雨型（雨峰系数 r={r}）",
                f"暴雨强度公式：{data['formula']}",
                f"总降雨量 {data['total_rainfall_mm']} mm，峰值雨强 {data['peak_intensity_mm_h']} mm/h 出现在第 {data['peak_time_min']} 分钟",
            ]
            return ModelResult(
                success=True, model_type="rainfall", operation="generate",
                data=data, notes=notes
            )
        except Exception as e:
            return ModelResult(
                success=False, model_type="rainfall", operation="generate",
                errors=[f"生成失败：{str(e)}"]
            )

    def generate_swmm_input(self, params: Dict[str, Any]) -> ModelResult:
        """生成SWMM输入文件"""
        try:
            data = generate_swmm_inp(
                project_name=params.get("project_name", "未命名项目"),
                subcatchments=params.get("subcatchments", []),
                junctions=params.get("junctions", []),
                conduits=params.get("conduits", []),
                outfalls=params.get("outfalls", []),
                rain_gauge=params.get("rain_gauge"),
            )
            return ModelResult(
                success=True, model_type="swmm", operation="generate_inp",
                data=data, warnings=data.get("warnings", []), notes=data.get("notes", [])
            )
        except Exception as e:
            return ModelResult(
                success=False, model_type="swmm", operation="generate_inp",
                errors=[f"生成失败：{str(e)}"]
            )

    def parse_swmm_report(self, rpt_content: str) -> ModelResult:
        """解析SWMM报告"""
        if not rpt_content or len(rpt_content) < 100:
            return ModelResult(
                success=False, model_type="swmm", operation="parse_rpt",
                errors=["RPT文件内容为空或过短，请检查文件"]
            )
        try:
            data = parse_swmm_rpt(rpt_content)
            return ModelResult(
                success=True, model_type="swmm", operation="parse_rpt",
                data=data, warnings=data.get("warnings", []), errors=data.get("errors", [])
            )
        except Exception as e:
            return ModelResult(
                success=False, model_type="swmm", operation="parse_rpt",
                errors=[f"解析失败：{str(e)}"]
            )

    def recommend_subcatchment_params(self, land_use: str, area_ha: float) -> Dict[str, Any]:
        """根据用地类型推荐子汇水区参数"""
        defaults = SUBCATCHMENT_DEFAULTS.get(land_use, SUBCATCHMENT_DEFAULTS["residential"])
        width = math.sqrt(area_ha * 10000) * 0.5 if area_ha > 0 else 100
        return {
            "land_use_name": defaults["name"],
            "n_imperv": defaults["n_imperv"],
            "n_perv": defaults["n_perv"],
            "s_imperv": defaults["s_imperv"],
            "s_perv": defaults["s_perv"],
            "pct_zero": defaults["pct_zero"],
            "pct_imperv": defaults["pct_imperv"],
            "recommended_width_m": round(width, 1),
        }


# 单例
hydro_model_assistant = HydroModelAssistant()
