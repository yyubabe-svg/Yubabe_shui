"""
水利工程常用计算引擎
包含：明渠均匀流、堤顶高程、雨水设计流量、管径校核、渠道断面、糙率选取、工程量汇总等
所有计算均有规范依据，输出包含：输入参数、计算公式、中间过程、结果、适用条件、引用依据
"""
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ChannelType(str, Enum):
    TRAPEZOIDAL = "trapezoidal"   # 梯形
    RECTANGULAR = "rectangular"   # 矩形
    CIRCULAR = "circular"         # 圆形（管道）
    TRIANGULAR = "triangular"     # 三角形


class RoughnessMaterial(str, Enum):
    CONCRETE = "concrete"            # 混凝土衬砌
    MORTAR_STONE = "mortar_stone"    # 浆砌石
    DRY_STONE = "dry_stone"          # 干砌石
    EARTH_CLEAN = "earth_clean"      # 良好土渠
    EARTH_NORMAL = "earth_normal"    # 一般土渠
    EARTH_WEEDY = "earth_weedy"      # 长草土渠
    ROCK = "rock"                    # 岩石渠道
    PVC_PIPE = "pvc_pipe"            # PVC/PE管
    CONCRETE_PIPE = "concrete_pipe"  # 混凝土管
    CAST_IRON = "cast_iron"          # 铸铁管
    STEEL = "steel"                  # 钢管


# 曼宁糙率系数参考表（SL/T 4-2020、GB 50288-2018等）
ROUGHNESS_TABLE = {
    RoughnessMaterial.CONCRETE: {"n": 0.014, "range": "0.011~0.018", "desc": "混凝土衬砌渠道/管道"},
    RoughnessMaterial.MORTAR_STONE: {"n": 0.025, "range": "0.020~0.030", "desc": "浆砌块石衬砌"},
    RoughnessMaterial.DRY_STONE: {"n": 0.033, "range": "0.028~0.040", "desc": "干砌块石衬砌"},
    RoughnessMaterial.EARTH_CLEAN: {"n": 0.022, "range": "0.020~0.025", "desc": "顺直清洁土渠"},
    RoughnessMaterial.EARTH_NORMAL: {"n": 0.027, "range": "0.025~0.030", "desc": "一般土渠（少量杂草）"},
    RoughnessMaterial.EARTH_WEEDY: {"n": 0.035, "range": "0.030~0.040", "desc": "长草土渠/弯曲段"},
    RoughnessMaterial.ROCK: {"n": 0.030, "range": "0.025~0.040", "desc": "岩石开挖渠道"},
    RoughnessMaterial.PVC_PIPE: {"n": 0.010, "range": "0.009~0.011", "desc": "PVC/PE塑料管"},
    RoughnessMaterial.CONCRETE_PIPE: {"n": 0.013, "range": "0.011~0.015", "desc": "混凝土管"},
    RoughnessMaterial.CAST_IRON: {"n": 0.013, "range": "0.012~0.015", "desc": "铸铁管"},
    RoughnessMaterial.STEEL: {"n": 0.012, "range": "0.011~0.014", "desc": "钢管"},
}


@dataclass
class CalcStep:
    """计算过程单步记录"""
    description: str
    formula: str
    inputs: Dict[str, Any]
    result: Any
    unit: str = ""


@dataclass
class CalcResult:
    """计算结果封装"""
    calc_type: str
    calc_name: str
    success: bool
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    steps: List[CalcStep] = field(default_factory=list)
    code_basis: str = ""
    notes: str = ""
    warnings: List[str] = field(default_factory=list)
    review_required: bool = True  # 是否需要人工复核


class HydraulicCalculator:
    """水利工程常用计算引擎"""

    # ==================== 明渠均匀流计算（曼宁公式） ====================
    def uniform_flow(self, params: Dict[str, Any]) -> CalcResult:
        """
        明渠均匀流计算（曼宁公式）
        Q = (1/n) * A * R^(2/3) * J^(1/2)
        输入参数:
            channel_type: 断面类型 trapezoidal/rectangular/circular/triangular
            b: 底宽 (m) [梯形/矩形]
            h: 水深 (m)
            m: 边坡系数 m=水平/垂直 [梯形/三角形]
            d: 管径 (m) [圆形]
            n: 曼宁糙率系数
            J: 渠道纵坡 (小数，如0.001)
            material: 材料类型（可选，若提供则自动查n）
        """
        channel_type = params.get("channel_type", ChannelType.TRAPEZOIDAL)
        b = float(params.get("b", 0))
        h = float(params.get("h", 0))
        m = float(params.get("m", 0))
        d = float(params.get("d", 0))
        n_input = params.get("n")
        material = params.get("material")
        J = float(params.get("J", 0))

        steps = []
        warnings = []

        # 确定糙率
        if material and not n_input:
            mat_key = RoughnessMaterial(material) if material in [e.value for e in RoughnessMaterial] else None
            if mat_key and mat_key in ROUGHNESS_TABLE:
                n = ROUGHNESS_TABLE[mat_key]["n"]
                steps.append(CalcStep(
                    description="查曼宁糙率系数表",
                    formula=f"n = {ROUGHNESS_TABLE[mat_key]['n']}",
                    inputs={"材料": ROUGHNESS_TABLE[mat_key]["desc"], "推荐范围": ROUGHNESS_TABLE[mat_key]["range"]},
                    result=n
                ))
            else:
                n = 0.025
                warnings.append("未识别的材料类型，糙率n默认取0.025")
        else:
            n = float(n_input) if n_input else 0.025

        # 计算过水断面面积A、湿周χ、水力半径R
        if channel_type == ChannelType.TRAPEZOIDAL:
            if b <= 0 or h <= 0:
                return CalcResult(
                    calc_type="uniform_flow", calc_name="明渠均匀流计算",
                    success=False, inputs=params, outputs={},
                    warnings=["梯形断面需要底宽b和水深h"]
                )
            A = (b + m * h) * h
            P = b + 2 * h * math.sqrt(1 + m ** 2)
            steps.append(CalcStep(
                description="计算过水断面面积",
                formula="A = (b + m·h)·h",
                inputs={"b": b, "m": m, "h": h}, result=round(A, 4), unit="m²"
            ))
            steps.append(CalcStep(
                description="计算湿周",
                formula="χ = b + 2h·√(1+m²)",
                inputs={"b": b, "m": m, "h": h}, result=round(P, 4), unit="m"
            ))
        elif channel_type == ChannelType.RECTANGULAR:
            if b <= 0 or h <= 0:
                return CalcResult(
                    calc_type="uniform_flow", calc_name="明渠均匀流计算",
                    success=False, inputs=params, outputs={},
                    warnings=["矩形断面需要底宽b和水深h"]
                )
            A = b * h
            P = b + 2 * h
            steps.append(CalcStep(description="过水断面面积(矩形)", formula="A = b·h",
                                  inputs={"b": b, "h": h}, result=round(A, 4), unit="m²"))
            steps.append(CalcStep(description="湿周(矩形)", formula="χ = b + 2h",
                                  inputs={"b": b, "h": h}, result=round(P, 4), unit="m"))
        elif channel_type == ChannelType.TRIANGULAR:
            if h <= 0 or m <= 0:
                return CalcResult(
                    calc_type="uniform_flow", calc_name="明渠均匀流计算",
                    success=False, inputs=params, outputs={},
                    warnings=["三角形断面需要水深h和边坡系数m"]
                )
            A = m * h ** 2
            P = 2 * h * math.sqrt(1 + m ** 2)
            steps.append(CalcStep(description="过水断面面积(三角形)", formula="A = m·h²",
                                  inputs={"m": m, "h": h}, result=round(A, 4), unit="m²"))
            steps.append(CalcStep(description="湿周(三角形)", formula="χ = 2h·√(1+m²)",
                                  inputs={"m": m, "h": h}, result=round(P, 4), unit="m"))
        elif channel_type == ChannelType.CIRCULAR:
            if d <= 0 or h <= 0:
                return CalcResult(
                    calc_type="uniform_flow", calc_name="明渠均匀流计算",
                    success=False, inputs=params, outputs={},
                    warnings=["圆形断面需要管径d和水深h"]
                )
            r = d / 2
            ratio = h / d
            if ratio > 1:
                warnings.append(f"水深h={h}m大于管径d={d}m，按满流计算")
                ratio = 1.0
                h = d
            theta = 2 * math.acos(1 - 2 * ratio)  # 圆心角(弧度)
            A = (r ** 2 / 8) * (2 * math.pi - theta + math.sin(theta)) if ratio < 1 else math.pi * r ** 2
            P = r * (2 * math.pi - theta) if ratio < 1 else math.pi * d
            steps.append(CalcStep(description="充满角计算", formula="θ = 2·arccos(1-2h/d)",
                                  inputs={"h": h, "d": d}, result=round(math.degrees(theta), 2), unit="°"))
            steps.append(CalcStep(description="过水断面面积(圆形)", formula="A = (r²/8)(2π-θ+sinθ)",
                                  inputs={"r": r, "theta_deg": round(math.degrees(theta), 2)},
                                  result=round(A, 4), unit="m²"))
            steps.append(CalcStep(description="湿周(圆形)", formula="χ = r(2π-θ)",
                                  inputs={"r": r}, result=round(P, 4), unit="m"))
        else:
            return CalcResult(
                calc_type="uniform_flow", calc_name="明渠均匀流计算",
                success=False, inputs=params, outputs={},
                warnings=[f"不支持的断面类型: {channel_type}"]
            )

        R = A / P if P > 0 else 0
        v = (1 / n) * (R ** (2 / 3)) * (J ** 0.5) if n > 0 and J > 0 else 0
        Q = A * v

        steps.append(CalcStep(description="水力半径", formula="R = A/χ",
                              inputs={"A": round(A, 4), "P": round(P, 4)}, result=round(R, 4), unit="m"))
        steps.append(CalcStep(description="平均流速(曼宁公式)", formula="v = (1/n)·R^(2/3)·J^(1/2)",
                              inputs={"n": n, "R": round(R, 4), "J": J}, result=round(v, 3), unit="m/s"))
        steps.append(CalcStep(description="设计流量", formula="Q = A·v",
                              inputs={"A": round(A, 4), "v": round(v, 3)}, result=round(Q, 4), unit="m³/s"))

        # 不冲不淤校核提示
        v_warning = ""
        if v > 3.0:
            warnings.append(f"流速{v:.2f}m/s较大，需校核渠道抗冲能力")
        elif v < 0.4:
            warnings.append(f"流速{v:.2f}m/s较小，可能产生淤积，建议不小于0.4m/s")

        return CalcResult(
            calc_type="uniform_flow",
            calc_name="明渠均匀流计算（曼宁公式）",
            success=True,
            inputs=params,
            outputs={
                "A_m2": round(A, 4),
                "P_m": round(P, 4),
                "R_m": round(R, 4),
                "v_m_s": round(v, 3),
                "Q_m3_s": round(Q, 4),
                "n": n,
            },
            steps=steps,
            code_basis="《灌溉与排水工程设计标准》GB 50288-2018、《渠道防渗工程技术规范》SL/T 4-2020 曼宁公式",
            notes="曼宁公式适用于均匀紊流阻力平方区，明渠和管道满流/非满流均可使用。"
                  "计算结果需人工复核，重要工程应通过物理模型试验验证。",
            warnings=warnings,
            review_required=True
        )

    # ==================== 雨水设计流量计算（推理公式法） ====================
    def storm_water_flow(self, params: Dict[str, Any]) -> CalcResult:
        """
        雨水设计流量（推理公式法 / 室外排水设计规范 GB 50014）
        Q = ψ · q · F
        q = 167·A1·(1+C·lgP)/(t+b)^n  （暴雨强度公式，按当地参数）
        简化版：q = 167·i，i为设计暴雨强度(mm/min)
        输入参数:
            psi: 径流系数ψ
            F: 汇水面积 (ha)
            P: 设计重现期 (年)，默认2
            t_min: 降雨历时 (min)，默认15
            i_mm_min: 设计暴雨强度 (mm/min)，若提供则直接用，否则用简化公式
            region: 地区（用于暴雨强度公式选参，如'chengdu'）
        """
        psi = float(params.get("psi", 0.6))
        F = float(params.get("F", 0))
        P = float(params.get("P", 2))
        t = float(params.get("t_min", 15))
        i_input = params.get("i_mm_min")
        region = params.get("region", "general")

        steps = []
        warnings = []

        # 径流系数参考
        psi_ref = {
            "各种屋面、混凝土和沥青路面": 0.90,
            "大块石铺砌路面、沥青表面处理碎石路面": 0.60,
            "级配碎石路面": 0.45,
            "干砌砖石和碎石路面": 0.40,
            "非铺砌土路面": 0.30,
            "公园和绿地": 0.15,
        }

        # 暴雨强度简化参数（按常用地区公式）
        # q = 167 * A1 * (1 + C*lgP) / (t + b)^n  (L/s·ha)
        region_params = {
            "chengdu": {"A1": 12.31, "C": 0.725, "b": 12.8, "n": 0.789, "desc": "成都地区暴雨强度公式"},
            "chongqing": {"A1": 15.03, "C": 0.785, "b": 10.0, "n": 0.753, "desc": "重庆地区暴雨强度公式"},
            "beijing": {"A1": 11.98, "C": 0.811, "b": 8.0, "n": 0.711, "desc": "北京地区暴雨强度公式"},
            "general": {"A1": 10.0, "C": 0.70, "b": 10.0, "n": 0.75, "desc": "通用简化暴雨强度公式（仅供参考）"},
        }
        rp = region_params.get(region, region_params["general"])

        steps.append(CalcStep(description="确定径流系数", formula="ψ",
                              inputs={"参考值": psi_ref, "采用值": psi}, result=psi))

        steps.append(CalcStep(description="汇水面积", formula="F",
                              inputs={}, result=F, unit="ha"))

        if i_input:
            i = float(i_input)
            q = 167 * i
            steps.append(CalcStep(description="设计暴雨强度(直接输入)", formula="i",
                                  inputs={}, result=i, unit="mm/min"))
        else:
            lgP = math.log10(P) if P > 0 else 0
            denom = (t + rp["b"]) ** rp["n"]
            q = 167 * rp["A1"] * (1 + rp["C"] * lgP) / denom
            i = q / 167
            steps.append(CalcStep(description=f"暴雨强度计算（{rp['desc']}）",
                                  formula="q = 167·A1(1+C·lgP)/(t+b)^n",
                                  inputs={"A1": rp["A1"], "C": rp["C"], "b": rp["b"], "n": rp["n"],
                                          "P": P, "t": t, "lgP": round(lgP, 3)},
                                  result=round(q, 2), unit="L/(s·ha)"))

        Q = psi * q * F  # L/s
        Q_m3_s = Q / 1000

        steps.append(CalcStep(description="雨水设计流量", formula="Q = ψ·q·F",
                              inputs={"ψ": psi, "q": round(q, 2), "F": F},
                              result=round(Q, 2), unit="L/s"))

        if psi < 0.1 or psi > 0.95:
            warnings.append(f"径流系数ψ={psi}超出常规范围(0.15~0.90)，请核实")
        if F <= 0:
            warnings.append("汇水面积F必须大于0")
        if region == "general":
            warnings.append("当前使用通用简化暴雨公式，实际工程应采用项目所在地的暴雨强度公式")

        return CalcResult(
            calc_type="storm_water_flow",
            calc_name="雨水设计流量计算（推理公式法）",
            success=F > 0,
            inputs=params,
            outputs={
                "psi": psi,
                "F_ha": F,
                "P_years": P,
                "t_min": t,
                "q_L_s_ha": round(q, 2),
                "i_mm_min": round(i, 3),
                "Q_L_s": round(Q, 2),
                "Q_m3_s": round(Q_m3_s, 4),
            },
            steps=steps,
            code_basis="《室外排水设计标准》GB 50014-2021 第5.2节 雨水设计流量",
            notes="推理公式法适用于汇水面积较小（一般F≤2km²）的城镇雨水管渠设计。"
                  "当汇水面积较大或地形复杂时，应采用数学模型法。",
            warnings=warnings,
            review_required=True
        )

    # ==================== 管径校核 ====================
    def pipe_check(self, params: Dict[str, Any]) -> CalcResult:
        """
        圆管管径校核（满流/非满流）
        输入参数:
            d: 管径 (m)
            Q: 设计流量 (m³/s)
            n: 曼宁糙率 (默认0.013混凝土管)
            J: 管道坡度 (小数)
            material: 管材(可选)
            max_v: 最大允许流速 (m/s，默认金属管10，非金属管5)
            min_v: 最小流速 (m/s，默认0.6)
            max_fill: 最大充满度（默认按管径查表）
        """
        d = float(params.get("d", 0))
        Q = float(params.get("Q", 0))
        n_input = params.get("n")
        material = params.get("material", RoughnessMaterial.CONCRETE_PIPE)
        J = float(params.get("J", 0.003))
        max_v = float(params.get("max_v", 5.0))
        min_v = float(params.get("min_v", 0.6))

        steps = []
        warnings = []

        if d <= 0 or Q <= 0:
            return CalcResult(
                calc_type="pipe_check", calc_name="圆管管径校核",
                success=False, inputs=params, outputs={},
                warnings=["管径d和设计流量Q必须大于0"]
            )

        # 确定糙率
        if material and not n_input:
            mat_key = RoughnessMaterial(material) if material in [e.value for e in RoughnessMaterial] else None
            n = ROUGHNESS_TABLE.get(mat_key, {}).get("n", 0.013) if mat_key else 0.013
        else:
            n = float(n_input) if n_input else 0.013

        # 满流水力计算
        A_full = math.pi * (d / 2) ** 2
        P_full = math.pi * d
        R_full = d / 4
        v_full = (1 / n) * (R_full ** (2 / 3)) * (J ** 0.5)
        Q_full = A_full * v_full

        steps.append(CalcStep(description="满流过水断面面积", formula="A = π(d/2)²",
                              inputs={"d": d}, result=round(A_full, 4), unit="m²"))
        steps.append(CalcStep(description="满流水力半径", formula="R = d/4",
                              inputs={"d": d}, result=round(R_full, 4), unit="m"))
        steps.append(CalcStep(description="满流流速", formula="v = (1/n)R^(2/3)J^(1/2)",
                              inputs={"n": n, "R": round(R_full, 4), "J": J},
                              result=round(v_full, 3), unit="m/s"))
        steps.append(CalcStep(description="满流输水能力", formula="Q满 = A·v",
                              inputs={"A": round(A_full, 4), "v": round(v_full, 3)},
                              result=round(Q_full, 4), unit="m³/s"))

        # 求非满流工况（牛顿迭代求解h）
        def calc_Q_at_h(h: float) -> float:
            if h <= 0: return 0
            if h >= d: return Q_full
            r = d / 2
            ratio = h / d
            theta = 2 * math.acos(1 - 2 * ratio)
            A = (r ** 2 / 8) * (2 * math.pi - theta + math.sin(theta))
            P = r * (2 * math.pi - theta)
            R = A / P
            v = (1 / n) * (R ** (2 / 3)) * (J ** 0.5)
            return A * v

        # 二分法求Q对应的水深
        h_lo, h_hi = 0, d
        for _ in range(60):
            h_mid = (h_lo + h_hi) / 2
            if calc_Q_at_h(h_mid) < Q:
                h_lo = h_mid
            else:
                h_hi = h_mid
            if abs(h_hi - h_lo) < 1e-5:
                break
        h_design = (h_lo + h_hi) / 2
        ratio_design = h_design / d

        # 校核充满度（GB 50014 表5.3.3）
        max_fill_table = {0.20: 0.55, 0.30: 0.55, 0.40: 0.65, 0.50: 0.70,
                          0.60: 0.70, 0.80: 0.75, 1.00: 0.80, 9.99: 0.80}
        # d以mm计查表
        d_mm = d * 1000
        max_fill = 0.55
        for d_lim in sorted(max_fill_table.keys()):
            if d_mm <= d_lim * 1000:
                max_fill = max_fill_table[d_lim]
                break

        # 校核流速
        # 设计工况流速
        r = d / 2
        theta_d = 2 * math.acos(1 - 2 * ratio_design)
        A_d = (r ** 2 / 8) * (2 * math.pi - theta_d + math.sin(theta_d))
        v_design = Q / A_d if A_d > 0 else 0

        fill_ok = ratio_design <= max_fill
        v_ok = min_v <= v_design <= max_v
        capacity_ok = Q <= Q_full

        steps.append(CalcStep(description="设计工况水深(迭代求解)", formula="Q(h)=Q设计",
                              inputs={"Q设计": Q}, result=round(h_design, 4), unit="m"))
        steps.append(CalcStep(description="设计充满度", formula="h/d",
                              inputs={"h": round(h_design, 4), "d": d},
                              result=round(ratio_design, 3), unit=""))
        steps.append(CalcStep(description="设计流速", formula="v = Q/A(h)",
                              inputs={"Q": Q, "A(h)": round(A_d, 4)},
                              result=round(v_design, 3), unit="m/s"))
        steps.append(CalcStep(description="最大允许充满度", formula="查GB 50014表5.3.3",
                              inputs={"d_mm": d_mm}, result=max_fill, unit=""))

        if not capacity_ok:
            warnings.append(f"设计流量Q={Q:.3f}m³/s超过满流能力Q满={Q_full:.3f}m³/s，管径不足！")
        if not fill_ok:
            warnings.append(f"设计充满度{ratio_design:.2f}超过规范允许最大值{max_fill}")
        if v_design > max_v:
            warnings.append(f"流速{v_design:.2f}m/s超过最大允许流速{max_v}m/s，需考虑管材耐冲刷能力")
        if v_design < min_v:
            warnings.append(f"流速{v_design:.2f}m/s低于最小不淤流速{min_v}m/s，可能淤积")

        # 推荐管径
        d_rec = d
        for trial_d in [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0]:
            if trial_d <= d: continue
            A_t = math.pi * (trial_d / 2) ** 2
            R_t = trial_d / 4
            v_t = (1 / n) * (R_t ** (2 / 3)) * (J ** 0.5)
            Q_t = A_t * v_t
            ratio_d = 0  # 迭代
            h_l, h_h = 0, trial_d
            for _ in range(40):
                h_m = (h_l + h_h) / 2
                def qf(hh):
                    if hh<=0:return 0
                    if hh>=trial_d:return Q_t
                    rr=trial_d/2; rt=hh/trial_d; th=2*math.acos(1-2*rt)
                    A=(rr**2/8)*(2*math.pi-th+math.sin(th)); P=rr*(2*math.pi-th); R=A/P
                    return A*(1/n)*(R**(2/3))*(J**0.5)
                if qf(h_m) < Q: h_l = h_m
                else: h_h = h_m
            h_d_t = (h_l + h_h) / 2
            ratio_t = h_d_t / trial_d
            v_t_actual = Q / (math.pi*(trial_d/2)**2 * (1 - (math.acos(1-2*ratio_t)*2 - math.sin(2*math.acos(1-2*ratio_t)))/(2*math.pi))) if False else 0
            # 简化：推荐下一管径
            if Q_t >= Q:
                d_rec = trial_d
                break

        return CalcResult(
            calc_type="pipe_check",
            calc_name="圆管管径校核",
            success=True,
            inputs=params,
            outputs={
                "d_m": d,
                "Q_design_m3_s": Q,
                "n": n,
                "J": J,
                "Q_full_m3_s": round(Q_full, 4),
                "v_full_m_s": round(v_full, 3),
                "h_design_m": round(h_design, 4),
                "fill_ratio": round(ratio_design, 3),
                "max_fill_allowed": max_fill,
                "v_design_m_s": round(v_design, 3),
                "capacity_ok": capacity_ok,
                "fill_ok": fill_ok,
                "v_ok": v_ok,
                "d_recommended_m": d_rec if not capacity_ok else d,
            },
            steps=steps,
            code_basis="《室外排水设计标准》GB 50014-2021 第5.3节 管道水力计算、表5.3.3最大设计充满度",
            notes="非金属管道最大流速一般不超过5m/s，金属管道不超过10m/s；"
                  "最小流速（不淤流速）一般不低于0.6m/s（雨水管）或0.75m/s（污水管）。",
            warnings=warnings,
            review_required=True
        )

    # ==================== 堤顶高程计算 ====================
    def levee_crest_elevation(self, params: Dict[str, Any]) -> CalcResult:
        """
        堤顶高程计算
        堤顶高程 = 设计洪水位 + 堤顶超高Y
        Y = R(波浪爬高) + e(风壅水面高) + A(安全加高)
        输入参数:
            design_water_level: 设计洪水位 (m)
            building_level: 堤防级别 (1~5)
            levee_type: 'earth'(土堤) 或 'concrete'(防洪墙)
            wind_speed: 计算风速 (m/s)，默认20
            fetch_length: 吹程 (km)，默认2.0
            wave_height: 直接给定波浪爬高R (m)，若提供则跳过计算
            wind_setup: 直接给定风壅高度e (m)
            safety_freeboard: 直接给定安全加高A (m)，否则查表
        """
        dwl = float(params.get("design_water_level", 0))
        bl = int(params.get("building_level", 4))
        lt = params.get("levee_type", "earth")
        ws = float(params.get("wind_speed", 20))
        fl = float(params.get("fetch_length", 2.0))
        R_input = params.get("wave_height")
        e_input = params.get("wind_setup")
        A_input = params.get("safety_freeboard")

        steps = []
        warnings = []

        # 安全加高（GB 50286-2013 表3.2.1）
        if A_input:
            A = float(A_input)
            steps.append(CalcStep(description="安全加高(直接输入)", formula="A", inputs={}, result=A, unit="m"))
        else:
            safety_table = {
                1: {"design": 1.0, "check": 0.5},
                2: {"design": 0.8, "check": 0.4},
                3: {"design": 0.7, "check": 0.3},
                4: {"design": 0.6, "check": 0.3},
                5: {"design": 0.6, "check": 0.3},
            }
            A = safety_table.get(bl, safety_table[5])["design"]
            if lt == "concrete":
                A = max(0.3, A - 0.2)
            steps.append(CalcStep(description="安全加高查表",
                                  formula=f"GB 50286-2013表3.2.1 ({bl}级堤)" +
                                          ("，防洪墙减0.2m" if lt == "concrete" else ""),
                                  inputs={"堤防级别": bl}, result=A, unit="m"))

        # 风壅水面高度（简化公式 e = (k·w²·F)/(2·g·d_m) ）
        if e_input:
            e = float(e_input)
            steps.append(CalcStep(description="风壅水面高(直接输入)", formula="e", inputs={}, result=e, unit="m"))
        else:
            # 简化：莆田公式 e = (0.00144·w²·F)/(H_m)
            # 这里用经验值（小河道通常0.01~0.05m）
            d_avg = float(params.get("avg_depth", 3.0))
            k = 3.6e-6  # 综合摩阻系数
            g = 9.81
            e = k * (ws ** 2) * (fl * 1000) / (g * d_avg)  # fl转换为m
            e = min(max(e, 0.005), 0.20)  # 限制合理范围
            steps.append(CalcStep(description="风壅水面高度(简化计算)",
                                  formula="e = k·w²·F/(g·d)",
                                  inputs={"w": ws, "F_km": fl, "d_avg": d_avg},
                                  result=round(e, 3), unit="m"))
            warnings.append("风壅水面高度为简化计算，重要堤防应按GB 50286附录B详细计算")

        # 波浪爬高（简化：R = KΔ·Kv·Rp，这里用经验估算）
        if R_input:
            R = float(R_input)
            steps.append(CalcStep(description="波浪爬高(直接输入)", formula="R", inputs={}, result=R, unit="m"))
        else:
            # 简化：按风速和吹程估算波高，再按斜坡糙渗系数估算爬高
            # 莆田公式：h = 0.0166·w^1.25·F^0.33 (m)
            h_wave = 0.0166 * (ws ** 1.25) * (fl ** 0.33)
            h_wave = min(max(h_wave, 0.1), 1.5)
            # 波浪爬高 R = K·h_wave，K与坡度、护面有关（m=2.5混凝土板护面取约2.0）
            K_R = float(params.get("wave_runup_coeff", 2.0))
            R = K_R * h_wave
            R = min(max(R, 0.3), 2.5)
            steps.append(CalcStep(description="设计波高估算(莆田公式)",
                                  formula="h = 0.0166·w^1.25·F^0.33",
                                  inputs={"w": ws, "F": fl}, result=round(h_wave, 3), unit="m"))
            steps.append(CalcStep(description="波浪爬高估算",
                                  formula="R = K·h",
                                  inputs={"K": K_R, "h": round(h_wave, 3)},
                                  result=round(R, 3), unit="m"))
            warnings.append("波浪爬高为简化估算，实际工程应按GB 50286附录C计算，考虑坡面糙率、渗透性等影响")

        Y = R + e + A
        crest_el = dwl + Y

        steps.append(CalcStep(description="堤顶超高合计", formula="Y = R + e + A",
                              inputs={"R": round(R, 3), "e": round(e, 3), "A": A},
                              result=round(Y, 3), unit="m"))
        steps.append(CalcStep(description="堤顶高程", formula="堤顶高程 = 设计洪水位 + Y",
                              inputs={"设计洪水位": dwl, "Y": round(Y, 3)},
                              result=round(crest_el, 3), unit="m"))

        return CalcResult(
            calc_type="levee_crest_elevation",
            calc_name="堤顶高程计算",
            success=True,
            inputs=params,
            outputs={
                "design_water_level_m": dwl,
                "R_wave_runup_m": round(R, 3),
                "e_wind_setup_m": round(e, 3),
                "A_safety_m": A,
                "Y_total_freeboard_m": round(Y, 3),
                "crest_elevation_m": round(crest_el, 3),
            },
            steps=steps,
            code_basis="《堤防工程设计规范》GB 50286-2013 第3.2节 堤顶高程",
            notes="堤顶高程应按设计洪水位加堤顶超高确定；当堤顶临河滩时，还应满足防汛抢险交通要求（堤顶宽度一般≥4m）。",
            warnings=warnings,
            review_required=True
        )

    # ==================== 工程量计算（梯形渠道） ====================
    def channel_earthwork(self, params: Dict[str, Any]) -> CalcResult:
        """
        梯形渠道挖填土方量计算
        输入参数:
            b: 渠底宽 (m)
            h: 设计水深 (m)
            m: 内坡系数
            freeboard: 超高 (m)，默认0.5
            m_out: 外坡系数 (若为填方)，默认1.5
            top_width_extra: 堤顶宽单侧附加 (m)，默认1.5
            length: 渠道长度 (m)
            ground_slope: 地面坡降（简化：按水平地面0）
            excavation_type: 'cut'(挖方)、'fill'(填方)、'balanced'(半挖半填)
        """
        b = float(params.get("b", 0))
        h = float(params.get("h", 0))
        m = float(params.get("m", 1.5))
        fb = float(params.get("freeboard", 0.5))
        m_out = float(params.get("m_out", 1.5))
        top_extra = float(params.get("top_width_extra", 1.5))
        length = float(params.get("length", 100))
        ex_type = params.get("excavation_type", "cut")

        steps = []
        warnings = []

        if b <= 0 or h <= 0 or length <= 0:
            return CalcResult(
                calc_type="channel_earthwork", calc_name="渠道土方量计算",
                success=False, inputs=params, outputs={},
                warnings=["底宽b、水深h、渠道长度L必须大于0"]
            )

        H = h + fb  # 渠道总高度(含超高)

        if ex_type == "cut":
            # 全挖方：上宽 = b + 2*m*H + 工作面(简化0.5*2)
            top_width = b + 2 * m * H
            area_cut = (b + top_width) / 2 * H
            area_fill = 0
            steps.append(CalcStep(description="渠道全深(含超高)", formula="H = h + 超高",
                                  inputs={"h": h, "超高": fb}, result=round(H, 3), unit="m"))
            steps.append(CalcStep(description="挖方梯形上口宽", formula="B = b + 2·m·H",
                                  inputs={"b": b, "m": m, "H": round(H, 3)},
                                  result=round(top_width, 3), unit="m"))
            steps.append(CalcStep(description="挖方断面积", formula="A = (b+B)/2·H",
                                  inputs={"b": b, "B": round(top_width, 3), "H": round(H, 3)},
                                  result=round(area_cut, 3), unit="m²"))
        elif ex_type == "fill":
            # 全填方
            top_width = b + 2 * top_extra
            base_width = top_width + 2 * m_out * H
            area_fill = (top_width + base_width) / 2 * H - (b + 2 * m * h) / 2 * h
            # 简化：填方断面=外轮廓-过水断面
            area_fill = max(area_fill, (top_width + base_width) / 2 * H * 0.8)
            area_cut = 0
            steps.append(CalcStep(description="填方渠道", formula="(顶宽+底宽)/2·H - 过水断面",
                                  inputs={}, result=round(area_fill, 3), unit="m²"))
        else:  # balanced 半挖半填（挖渠土筑堤）
            cut_depth = H * 0.5
            fill_height = H * 0.5
            top_width_cut = b + 2 * m * cut_depth
            area_cut = (b + top_width_cut) / 2 * cut_depth
            # 两侧堤填方量
            dike_width = top_extra
            dike_area_single = dike_width * fill_height + (m_out * fill_height ** 2) / 2 + (m * fill_height ** 2) / 2
            area_fill = dike_area_single * 2
            steps.append(CalcStep(description="半挖半填(简化0.5H挖/填)", formula="",
                                  inputs={"挖深": cut_depth, "填高": fill_height},
                                  result={"挖方": round(area_cut, 3), "填方": round(area_fill, 3)},
                                  unit="m²"))

        vol_cut = area_cut * length
        vol_fill = area_fill * length

        steps.append(CalcStep(description="挖方量", formula="V挖 = A挖·L",
                              inputs={"A挖": round(area_cut, 3), "L": length},
                              result=round(vol_cut, 2), unit="m³"))
        steps.append(CalcStep(description="填方量", formula="V填 = A填·L",
                              inputs={"A填": round(area_fill, 3), "L": length},
                              result=round(vol_fill, 2), unit="m³"))

        # 衬砌面积（边坡+渠底）
        lining_area = (b + 2 * h * math.sqrt(1 + m ** 2)) * length
        steps.append(CalcStep(description="衬砌面积(边坡+渠底)", formula="S = (b + 2h·√(1+m²))·L",
                              inputs={"b": b, "h": h, "m": m, "L": length},
                              result=round(lining_area, 2), unit="m²"))

        return CalcResult(
            calc_type="channel_earthwork",
            calc_name="渠道土方量与衬砌工程量计算",
            success=True,
            inputs=params,
            outputs={
                "H_total_m": round(H, 3),
                "cut_area_m2": round(area_cut, 3),
                "fill_area_m2": round(area_fill, 3),
                "cut_volume_m3": round(vol_cut, 2),
                "fill_volume_m3": round(vol_fill, 2),
                "lining_area_m2": round(lining_area, 2),
                "length_m": length,
            },
            steps=steps,
            code_basis="《水利水电工程工程量计算规范》及渠道断面设计经验公式",
            notes="工程量为几何量计算，不含施工超挖超填量、损耗量和施工附加量。"
                  "概预算编制时应按相应定额乘以扩大系数（挖方超挖约5~10%，填方压实约10~15%）。",
            warnings=warnings,
            review_required=True
        )

    # ==================== 获取计算类型列表 ====================
    def get_calc_types(self) -> List[Dict[str, Any]]:
        """获取所有支持的计算类型及其参数说明"""
        return [
            {
                "id": "uniform_flow",
                "name": "明渠均匀流计算",
                "category": "水力计算",
                "desc": "曼宁公式计算渠道/管道过水能力、流速、水力半径",
                "params": [
                    {"key": "channel_type", "label": "断面类型", "type": "select",
                     "options": [
                         {"value": "trapezoidal", "label": "梯形"},
                         {"value": "rectangular", "label": "矩形"},
                         {"value": "triangular", "label": "三角形"},
                         {"value": "circular", "label": "圆形"}
                     ], "default": "trapezoidal"},
                    {"key": "b", "label": "底宽 b", "type": "number", "unit": "m", "default": 2.0, "hint": "梯形/矩形必填"},
                    {"key": "h", "label": "水深 h", "type": "number", "unit": "m", "default": 1.0, "required": True},
                    {"key": "m", "label": "边坡系数 m", "type": "number", "unit": "", "default": 1.5, "hint": "水平/垂直，梯形/三角形必填"},
                    {"key": "d", "label": "管径 d", "type": "number", "unit": "m", "default": 0, "hint": "圆形断面必填"},
                    {"key": "J", "label": "渠道纵坡 J", "type": "number", "unit": "", "default": 0.001, "required": True},
                    {"key": "material", "label": "渠道材料", "type": "select",
                     "options": [
                         {"value": "", "label": "自定义糙率n"},
                         {"value": "concrete", "label": "混凝土衬砌(n=0.014)"},
                         {"value": "mortar_stone", "label": "浆砌块石(n=0.025)"},
                         {"value": "dry_stone", "label": "干砌块石(n=0.033)"},
                         {"value": "earth_clean", "label": "顺直清洁土渠(n=0.022)"},
                         {"value": "earth_normal", "label": "一般土渠(n=0.027)"},
                         {"value": "earth_weedy", "label": "长草土渠(n=0.035)"},
                         {"value": "rock", "label": "岩石渠道(n=0.030)"},
                         {"value": "pvc_pipe", "label": "PVC/PE管(n=0.010)"},
                         {"value": "concrete_pipe", "label": "混凝土管(n=0.013)"},
                     ], "default": "concrete"},
                    {"key": "n", "label": "曼宁糙率 n", "type": "number", "unit": "", "default": 0, "hint": "若选了材料可留空自动查表"},
                ],
                "code_basis": "GB 50288-2018、SL/T 4-2020"
            },
            {
                "id": "storm_water_flow",
                "name": "雨水设计流量计算",
                "category": "排水/管网",
                "desc": "推理公式法计算雨水管渠设计流量",
                "params": [
                    {"key": "psi", "label": "径流系数 ψ", "type": "number", "unit": "", "default": 0.65, "required": True},
                    {"key": "F", "label": "汇水面积 F", "type": "number", "unit": "ha(公顷)", "default": 10, "required": True},
                    {"key": "P", "label": "设计重现期 P", "type": "number", "unit": "年", "default": 2},
                    {"key": "t_min", "label": "降雨历时 t", "type": "number", "unit": "min", "default": 15},
                    {"key": "region", "label": "暴雨公式地区", "type": "select",
                     "options": [
                         {"value": "chengdu", "label": "成都"},
                         {"value": "chongqing", "label": "重庆"},
                         {"value": "beijing", "label": "北京"},
                         {"value": "general", "label": "通用简化(仅供参考)"}
                     ], "default": "chengdu"},
                ],
                "code_basis": "GB 50014-2021"
            },
            {
                "id": "pipe_check",
                "name": "圆管管径校核",
                "category": "排水/管网",
                "desc": "校核圆管输水能力、充满度、流速是否满足规范",
                "params": [
                    {"key": "d", "label": "管径 d", "type": "number", "unit": "m", "default": 0.8, "required": True},
                    {"key": "Q", "label": "设计流量 Q", "type": "number", "unit": "m³/s", "default": 0.5, "required": True},
                    {"key": "J", "label": "管道坡度 J", "type": "number", "unit": "", "default": 0.003},
                    {"key": "material", "label": "管材", "type": "select",
                     "options": [
                         {"value": "concrete_pipe", "label": "混凝土管(n=0.013)"},
                         {"value": "pvc_pipe", "label": "PVC/PE管(n=0.010)"},
                         {"value": "cast_iron", "label": "铸铁管(n=0.013)"},
                         {"value": "steel", "label": "钢管(n=0.012)"},
                     ], "default": "concrete_pipe"},
                ],
                "code_basis": "GB 50014-2021 第5.3节"
            },
            {
                "id": "levee_crest_elevation",
                "name": "堤顶高程计算",
                "category": "防洪/堤防",
                "desc": "根据设计洪水位+波浪爬高+风壅高度+安全加高计算堤顶高程",
                "params": [
                    {"key": "design_water_level", "label": "设计洪水位", "type": "number", "unit": "m", "default": 100.0, "required": True},
                    {"key": "building_level", "label": "堤防级别", "type": "select",
                     "options": [
                         {"value": 1, "label": "1级"},
                         {"value": 2, "label": "2级"},
                         {"value": 3, "label": "3级"},
                         {"value": 4, "label": "4级"},
                         {"value": 5, "label": "5级"}
                     ], "default": 4},
                    {"key": "levee_type", "label": "堤防类型", "type": "select",
                     "options": [
                         {"value": "earth", "label": "土堤"},
                         {"value": "concrete", "label": "防洪墙/混凝土堤"}
                     ], "default": "earth"},
                    {"key": "wind_speed", "label": "计算风速", "type": "number", "unit": "m/s", "default": 20},
                    {"key": "fetch_length", "label": "吹程", "type": "number", "unit": "km", "default": 2.0},
                ],
                "code_basis": "GB 50286-2013 第3.2节"
            },
            {
                "id": "channel_earthwork",
                "name": "渠道土方与衬砌工程量",
                "category": "工程量计算",
                "desc": "计算渠道挖填土方量、混凝土衬砌面积",
                "params": [
                    {"key": "b", "label": "渠底宽 b", "type": "number", "unit": "m", "default": 2.0, "required": True},
                    {"key": "h", "label": "设计水深 h", "type": "number", "unit": "m", "default": 1.0, "required": True},
                    {"key": "m", "label": "内坡系数 m", "type": "number", "unit": "", "default": 1.5},
                    {"key": "freeboard", "label": "堤顶超高", "type": "number", "unit": "m", "default": 0.5},
                    {"key": "length", "label": "渠道长度 L", "type": "number", "unit": "m", "default": 1000},
                    {"key": "excavation_type", "label": "挖填类型", "type": "select",
                     "options": [
                         {"value": "cut", "label": "全挖方"},
                         {"value": "fill", "label": "全填方"},
                         {"value": "balanced", "label": "半挖半填"}
                     ], "default": "cut"},
                ],
                "code_basis": "水利工程量计算规范"
            },
        ]

    def calculate(self, calc_type: str, params: Dict[str, Any]) -> CalcResult:
        """统一计算入口"""
        calc_map = {
            "uniform_flow": self.uniform_flow,
            "storm_water_flow": self.storm_water_flow,
            "pipe_check": self.pipe_check,
            "levee_crest_elevation": self.levee_crest_elevation,
            "channel_earthwork": self.channel_earthwork,
        }
        func = calc_map.get(calc_type)
        if not func:
            return CalcResult(
                calc_type=calc_type, calc_name="未知计算类型",
                success=False, inputs=params, outputs={},
                warnings=[f"不支持的计算类型：{calc_type}"]
            )
        return func(params)


# 全局实例
hydraulic_calculator = HydraulicCalculator()


def calc_result_to_dict(cr: CalcResult) -> Dict[str, Any]:
    """将CalcResult转为可JSON序列化的dict"""
    return {
        "calc_type": cr.calc_type,
        "calc_name": cr.calc_name,
        "success": cr.success,
        "inputs": cr.inputs,
        "outputs": cr.outputs,
        "steps": [
            {
                "description": s.description,
                "formula": s.formula,
                "inputs": s.inputs,
                "result": s.result,
                "unit": s.unit,
            }
            for s in cr.steps
        ],
        "code_basis": cr.code_basis,
        "notes": cr.notes,
        "warnings": cr.warnings,
        "review_required": cr.review_required,
    }
