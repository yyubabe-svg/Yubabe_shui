from typing import Dict, Any, Optional
from .base import BaseTool, ToolCallResult, ToolParameter


class ParamCalculatorTool(BaseTool):
    name = "param_calculator"
    description = "水利工程参数计算与规范查表工具，支持工程等别判定、建筑物级别确定、防洪标准查算、坝顶超高计算等确定性计算，所有结果均有规范依据"
    parameters = [
        ToolParameter(
            name="calc_type",
            type="string",
            description="计算类型，可选值：'project_grade'(工程等别判定)、'building_level'(建筑物级别)、'flood_standard'(防洪标准)、'dam_freeboard'(坝顶超高)、'levee_freeboard'(堤顶超高)、'slope_safety_factor'(边坡稳定安全系数)、'return_period_convert'(重现期换算)",
            required=True,
            enum=["project_grade", "building_level", "flood_standard", "dam_freeboard", "levee_freeboard", "slope_safety_factor", "return_period_convert"],
        ),
        ToolParameter(
            name="parameters",
            type="object",
            description="计算参数字典，根据calc_type不同传入不同参数",
            required=True,
        ),
    ]

    async def ainvoke(self, calc_type: str, parameters: Dict[str, Any], **kwargs) -> ToolCallResult:
        try:
            if calc_type == "project_grade":
                return self._calc_project_grade(parameters)
            elif calc_type == "building_level":
                return self._calc_building_level(parameters)
            elif calc_type == "flood_standard":
                return self._calc_flood_standard(parameters)
            elif calc_type == "dam_freeboard":
                return self._calc_dam_freeboard(parameters)
            elif calc_type == "levee_freeboard":
                return self._calc_levee_freeboard(parameters)
            elif calc_type == "slope_safety_factor":
                return self._calc_slope_safety_factor(parameters)
            elif calc_type == "return_period_convert":
                return self._calc_return_period(parameters)
            else:
                return ToolCallResult(success=False, error=f"不支持的计算类型：{calc_type}")
        except Exception as e:
            return ToolCallResult(success=False, error=f"计算出错：{str(e)}")

    def _calc_project_grade(self, params: Dict) -> ToolCallResult:
        """工程等别判定（依据SL 252-2017 表3.0.1）"""
        storage = params.get("storage", 0)  # 总库容（万m³）
        power = params.get("power", 0)  # 装机容量（MW）
        farmland = params.get("farmland", 0)  # 保护农田（万亩）
        protect_population = params.get("protect_population", 0)  # 保护人口（万人）
        project_type = params.get("project_type", "reservoir")  # 工程类型

        # 自动识别单位：如果storage<10，假设是亿m³输入，转换为万m³
        if 0 < storage < 10:
            storage = storage * 10000  # 亿m³ → 万m³

        candidates = []

        # 1. 按库容判定（水库工程）
        if storage > 0:
            if storage >= 100000:  # ≥10亿m³
                g, desc = "I", "Ⅰ等（大(1)型）"
            elif storage >= 10000:  # 1~10亿m³
                g, desc = "II", "Ⅱ等（大(2)型）"
            elif storage >= 1000:  # 0.1~1亿m³
                g, desc = "III", "Ⅲ等（中型）"
            elif storage >= 100:  # 0.01~0.1亿m³
                g, desc = "IV", "Ⅳ等（小(1)型）"
            elif storage >= 10:  # 0.001~0.01亿m³
                g, desc = "V", "Ⅴ等（小(2)型）"
            else:
                g, desc = "V", "Ⅴ等以下（塘坝）"
            candidates.append(("库容", g, desc, f"总库容{storage}万m³"))

        # 2. 按装机容量判定（水电站）
        if power > 0:
            if power >= 1200:  # ≥1200MW
                g, desc = "I", "Ⅰ等"
            elif power >= 300:  # 300~1200MW
                g, desc = "II", "Ⅱ等"
            elif power >= 50:  # 50~300MW
                g, desc = "III", "Ⅲ等"
            elif power >= 10:  # 10~50MW
                g, desc = "IV", "Ⅳ等"
            else:
                g, desc = "V", "Ⅴ等"
            candidates.append(("装机容量", g, desc, f"装机{power}MW"))

        # 3. 按保护农田判定（防洪/灌溉工程）
        if farmland > 0:
            if farmland >= 500:  # ≥500万亩
                g, desc = "I", "Ⅰ等"
            elif farmland >= 100:  # 100~500万亩
                g, desc = "II", "Ⅱ等"
            elif farmland >= 30:  # 30~100万亩
                g, desc = "III", "Ⅲ等"
            elif farmland >= 5:  # 5~30万亩
                g, desc = "IV", "Ⅳ等"
            else:
                g, desc = "V", "Ⅴ等"
            candidates.append(("保护农田", g, desc, f"保护农田{farmland}万亩"))

        # 4. 按保护人口判定
        if protect_population > 0:
            if protect_population >= 150:  # ≥150万人
                g, desc = "I", "Ⅰ等"
            elif protect_population >= 50:  # 50~150万人
                g, desc = "II", "Ⅱ等"
            elif protect_population >= 20:  # 20~50万人
                g, desc = "III", "Ⅲ等"
            elif protect_population >= 5:  # 5~20万人
                g, desc = "IV", "Ⅳ等"
            else:
                g, desc = "V", "Ⅴ等"
            candidates.append(("保护人口", g, desc, f"保护人口{protect_population}万人"))

        # 取最高等别（I>II>III>IV>V）
        grade_order = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
        if candidates:
            best = min(candidates, key=lambda x: grade_order.get(x[1], 9))
            final_grade = best[1]
            final_desc = best[2]
            final_basis = f"按{best[0]}指标：{best[3]}"
        else:
            final_grade = "V"
            final_desc = "Ⅴ等（默认）"
            final_basis = "未提供判定指标，默认按V等"

        grade_names = {"I": "Ⅰ等", "II": "Ⅱ等", "III": "Ⅲ等", "IV": "Ⅳ等", "V": "Ⅴ等"}
        scale_names = {
            "I": "大(1)型", "II": "大(2)型", "III": "中型",
            "IV": "小(1)型", "V": "小(2)型"
        }

        return ToolCallResult(
            success=True,
            data={
                "calc_type": "工程等别判定",
                "input_params": params,
                "result": {
                    "grade": final_grade,
                    "grade_name": grade_names.get(final_grade, final_grade),
                    "scale": scale_names.get(final_grade, ""),
                    "basis": final_basis,
                    "all_indicators": [
                        {"指标": c[0], "判定等别": c[1], "规模": c[2], "依据": c[3]}
                        for c in candidates
                    ] if candidates else [],
                },
                "code_basis": "《水利水电工程等级划分及洪水标准》SL 252-2017 第3.0.1条、表3.0.1",
                "note": "⚠️ 工程等别应按其所承担的各项任务及指标中最高等别确定（就高不就低）",
            },
            references=[{
                "file_name": "《水利水电工程等级划分及洪水标准》SL 252-2017",
                "page_number": "第3.0.1条、表3.0.1",
                "snippet": "水利水电工程按其规模、效益和在经济社会中的重要性划分为五等；综合利用的水利水电工程，当按各综合利用项目的分等指标确定的等别不同时，其工程等别应按其中最高等别确定。",
            }],
        )

    def _calc_building_level(self, params: Dict) -> ToolCallResult:
        """建筑物级别判定"""
        project_grade = params.get("project_grade", "")  # I, II, III, IV, V
        is_main = params.get("is_main", True)  # 主要建筑物/次要建筑物
        is_special = params.get("is_special", False)  # 特殊情况（高坝、地质复杂等）

        grade_map_main = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
        grade_map_secondary = {"I": 3, "II": 3, "III": 4, "IV": 5, "V": 5}

        if is_main:
            level = grade_map_main.get(project_grade.upper(), 5)
            building_type = "主要建筑物"
            if is_special and level > 2:
                level = level - 1  # 特殊情况提高一级
                note = "因工程特殊（高坝/地质条件复杂/位置重要），建筑物级别提高一级"
            else:
                note = ""
        else:
            level = grade_map_secondary.get(project_grade.upper(), 5)
            building_type = "次要建筑物"
            note = ""

        return ToolCallResult(
            success=True,
            data={
                "calc_type": "建筑物级别判定",
                "input_params": params,
                "result": {
                    "level": level,
                    "building_type": building_type,
                    "level_name": f"{level}级",
                },
                "code_basis": "《水利水电工程等级划分及洪水标准》SL 252-2017 第4.0.1条",
                "note": note,
            },
            references=[{
                "file_name": "《水利水电工程等级划分及洪水标准》SL 252-2017",
                "page_number": "第4.0.1条",
                "snippet": "水工建筑物级别根据工程等别和建筑物重要性确定",
            }],
        )

    def _calc_flood_standard(self, params: Dict) -> ToolCallResult:
        """防洪标准查算"""
        building_level = params.get("building_level", 5)
        dam_type = params.get("dam_type", "earth")  # earth(土石坝), concrete(混凝土坝)

        # 山区丘陵区水库防洪标准（SL 252-2017表5.0.1）
        standards = {
            1: {"design": "1000~500年一遇", "check_earth": "可能最大洪水(PMF)~10000年一遇", "check_concrete": "5000~2000年一遇"},
            2: {"design": "500~100年一遇", "check_earth": "5000~2000年一遇", "check_concrete": "2000~1000年一遇"},
            3: {"design": "100~50年一遇", "check_earth": "2000~1000年一遇", "check_concrete": "1000~500年一遇"},
            4: {"design": "50~30年一遇", "check_earth": "1000~300年一遇", "check_concrete": "500~200年一遇"},
            5: {"design": "30~20年一遇", "check_earth": "500~200年一遇", "check_concrete": "300~100年一遇"},
        }

        std = standards.get(building_level, standards[5])
        check = std["check_earth"] if dam_type == "earth" else std["check_concrete"]

        return ToolCallResult(
            success=True,
            data={
                "calc_type": "防洪标准查算",
                "input_params": params,
                "result": {
                    "design_flood": std["design"],
                    "check_flood": check,
                },
                "code_basis": "《水利水电工程等级划分及洪水标准》SL 252-2017 表5.0.1",
                "note": "以上为山区丘陵区水库标准，平原区、滨海区需另查对应表格；土石坝防洪标准高于混凝土坝",
            },
            references=[{
                "file_name": "《水利水电工程等级划分及洪水标准》SL 252-2017",
                "page_number": "表5.0.1",
                "snippet": "水库工程水工建筑物防洪标准按建筑物级别确定",
            }],
        )

    def _calc_dam_freeboard(self, params: Dict) -> ToolCallResult:
        """坝顶超高计算（简化版）"""
        building_level = params.get("building_level", 5)
        dam_type = params.get("dam_type", "earth")

        # 安全超高值（SL 274-2020表5.1.1 土石坝）
        freeboard_map_earth = {1: 1.5, 2: 1.0, 3: 0.7, 4: 0.5, 5: 0.5}
        # 重力坝（SL 319-2018表A.0.1）
        freeboard_map_concrete = {1: 0.7, 2: 0.5, 3: 0.4, 4: 0.3, 5: 0.3}

        if dam_type == "earth":
            safety = freeboard_map_earth.get(building_level, 0.5)
            code = "《碾压式土石坝设计规范》SL 274-2020 表5.1.1"
        else:
            safety = freeboard_map_concrete.get(building_level, 0.3)
            code = "《混凝土重力坝设计规范》SL 319-2018"

        return ToolCallResult(
            success=True,
            data={
                "calc_type": "坝顶安全超高",
                "input_params": params,
                "result": {
                    "safety_freeboard_m": safety,
                    "formula": "坝顶超高 = 波浪爬高 + 风壅水面高度 + 安全超高",
                    "note": "以上仅为安全超高值，波浪爬高和风壅高度需根据风速、吹程等具体计算，坝顶高程应不低于水库静水位加坝顶超高",
                },
                "code_basis": code,
            },
            references=[{
                "file_name": code.split()[0],
                "page_number": "坝顶超高章节",
                "snippet": "坝顶超高应根据波浪爬高、风壅水面高度和安全超高确定",
            }],
        )

    def _calc_return_period(self, params: Dict) -> ToolCallResult:
        """重现期换算"""
        return_period = params.get("return_period", 0)  # 年
        frequency = params.get("frequency", 0)  # 频率(%)

        if return_period > 0:
            freq = (1 / return_period) * 100
            return ToolCallResult(
                success=True,
                data={
                    "calc_type": "重现期换算",
                    "input_params": params,
                    "result": {
                        "return_period_years": return_period,
                        "frequency_percent": round(freq, 4),
                        "description": f"{return_period}年一遇 ≈ 年频率{freq:.4f}%",
                    },
                    "formula": "P(%) = 1/T × 100%，T为重现期（年）",
                },
            )
        elif frequency > 0:
            t = 100 / frequency
            return ToolCallResult(
                success=True,
                data={
                    "calc_type": "重现期换算",
                    "input_params": params,
                    "result": {
                        "frequency_percent": frequency,
                        "return_period_years": round(t, 2),
                        "description": f"频率{frequency}% ≈ {round(t, 1)}年一遇",
                    },
                    "formula": "T = 100/P(%)，P为频率（%）",
                },
            )
        else:
            return ToolCallResult(success=False, error="请提供return_period（重现期）或frequency（频率%）")

    def _calc_levee_freeboard(self, params: Dict) -> ToolCallResult:
        """堤顶超高计算（依据GB 50286-2013《堤防工程设计规范》）"""
        building_level = params.get("building_level", 5)
        levee_type = params.get("levee_type", "earth")  # earth(土堤), concrete(防洪墙)
        flood_condition = params.get("flood_condition", "design")  # design(设计洪水), check(校核洪水)

        # 堤顶安全加高值（GB 50286-2013 表3.2.1）
        # 1级堤防：设计1.0m，校核0.5m
        # 2级堤防：设计0.8m，校核0.4m
        # 3级堤防：设计0.7m，校核0.3m
        # 4、5级堤防：设计0.6m，校核0.3m
        # 防洪墙：安全加高可减少0.2m
        safety_table = {
            1: {"design": 1.0, "check": 0.5},
            2: {"design": 0.8, "check": 0.4},
            3: {"design": 0.7, "check": 0.3},
            4: {"design": 0.6, "check": 0.3},
            5: {"design": 0.6, "check": 0.3},
        }
        std = safety_table.get(building_level, safety_table[5])
        safety = std[flood_condition]
        if levee_type == "concrete":
            safety = max(0.3, safety - 0.2)

        return ToolCallResult(
            success=True,
            data={
                "calc_type": "堤顶超高",
                "input_params": params,
                "result": {
                    "safety_freeboard_m": safety,
                    "formula": "堤顶超高 Y = R(波浪爬高) + e(风壅水面高) + A(安全加高)",
                    "levee_type": "土堤" if levee_type == "earth" else "防洪墙/混凝土堤",
                    "flood_condition": "设计洪水条件" if flood_condition == "design" else "校核洪水条件",
                },
                "code_basis": "《堤防工程设计规范》GB 50286-2013 第3.2.1条、表3.2.1",
                "note": "以上为安全加高A值，完整堤顶超高还需计算波浪爬高R和风壅水面高度e；1、2级堤防堤顶高程应按设计洪水位加堤顶超高确定。",
            },
            references=[{
                "file_name": "《堤防工程设计规范》GB 50286-2013",
                "page_number": "第3.2.1条",
                "snippet": "堤顶高程应按设计洪水位或设计高潮位加堤顶超高确定；堤顶超高应按波浪爬高、风壅水面高度和安全加高之和确定。",
            }],
        )

    def _calc_slope_safety_factor(self, params: Dict) -> ToolCallResult:
        """边坡稳定安全系数查询（依据各类坝工设计规范）"""
        building_level = params.get("building_level", 5)
        dam_type = params.get("dam_type", "earth")  # earth(土石坝), concrete(混凝土坝)
        condition = params.get("condition", "normal")  # normal(正常运用), very(非常运用), earthquake(地震工况)
        slope_type = params.get("slope_type", "upstream")  # upstream(上游坡), downstream(下游坡)

        # 碾压式土石坝边坡稳定最小安全系数（SL 274-2001 表8.3.10）
        if dam_type == "earth":
            factor_table = {
                1: {"normal": 1.50, "very": 1.30, "earthquake": 1.20},
                2: {"normal": 1.40, "very": 1.25, "earthquake": 1.15},
                3: {"normal": 1.30, "very": 1.20, "earthquake": 1.10},
                4: {"normal": 1.25, "very": 1.15, "earthquake": 1.05},
                5: {"normal": 1.20, "very": 1.10, "earthquake": 1.05},
            }
            code_name = "《碾压式土石坝设计规范》SL 274-2001"
            code_table = "表8.3.10"
        else:
            # 混凝土重力坝（SL 319-2018 表6.3.3）
            factor_table = {
                1: {"normal": 1.50, "very": 1.30, "earthquake": 1.20},
                2: {"normal": 1.40, "very": 1.25, "earthquake": 1.10},
                3: {"normal": 1.30, "very": 1.20, "earthquake": 1.10},
                4: {"normal": 1.25, "very": 1.15, "earthquake": 1.05},
                5: {"normal": 1.20, "very": 1.10, "earthquake": 1.00},
            }
            code_name = "《混凝土重力坝设计规范》SL 319-2018"
            code_table = "表6.3.3"

        std = factor_table.get(building_level, factor_table[5])
        factor = std[condition]
        condition_names = {
            "normal": "正常运用条件（稳定渗流期、设计洪水位）",
            "very": "非常运用条件（校核洪水位、水位骤降期）",
            "earthquake": "非常运用条件+地震（地震工况）",
        }

        return ToolCallResult(
            success=True,
            data={
                "calc_type": "边坡稳定最小安全系数",
                "input_params": params,
                "result": {
                    "min_safety_factor": factor,
                    "condition": condition_names.get(condition, condition),
                    "slope_type": "上游坡" if slope_type == "upstream" else "下游坡",
                    "all_factors": {
                        "正常运用": std["normal"],
                        "非常运用": std["very"],
                        "地震工况": std["earthquake"],
                    },
                },
                "code_basis": f"{code_name} {code_table}",
                "note": f"边坡稳定计算采用计及条块间作用力的方法时，{building_level}级建筑物{condition_names[condition]}下的坝坡抗滑稳定最小安全系数为{factor}。",
            },
            references=[{
                "file_name": code_name,
                "page_number": code_table,
                "snippet": "坝坡抗滑稳定安全系数不应小于规范规定值。",
            }],
        )
