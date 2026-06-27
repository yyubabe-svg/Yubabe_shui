"""报告章节模板Seed数据 - 按SL/T 619-2021初步设计报告编制规程"""
from sqlalchemy.orm import Session
from app.models.report_section import ReportSectionTemplate


# 初步设计报告标准章节结构（SL/T 619-2021）
PRELIMINARY_DESIGN_CHAPTERS = [
    {
        "chapter_number": "1",
        "title": "综合说明",
        "level": 1,
        "sort_order": 1,
        "writing_prompt": "扼要说明工程地理位置、建设缘由、工程任务和规模、工程布置及主要建筑物、施工组织、工程占地、移民安置、环境保护、水土保持、工程管理、设计概算、经济评价等主要内容和结论，附工程位置图和工程总布置图。",
        "required_params": ["project_name", "location", "project_grade", "scale_type", "main_building_level", "flood_std_design", "flood_std_check", "total_investment", "construction_period"],
        "reference_keywords": ["综合说明", "项目概况", "工程特性表", "结论与建议"],
        "children": [
            {"chapter_number": "1.1", "title": "工程概况", "writing_prompt": "说明工程名称、地理位置、所在河流、建设缘由、工程任务、工程等级及建筑物级别、建设过程等。"},
            {"chapter_number": "1.2", "title": "水文", "writing_prompt": "简述流域自然地理概况、水文测站分布及资料情况、径流、洪水、泥沙等主要成果。"},
            {"chapter_number": "1.3", "title": "工程地质", "writing_prompt": "简述区域地质、水库区地质、坝（闸）址及主要建筑物工程地质条件及结论。"},
            {"chapter_number": "1.4", "title": "工程任务和规模", "writing_prompt": "简述工程开发任务、防洪、供水、灌溉、发电等综合利用要求、水利计算成果、工程规模及特征水位。"},
            {"chapter_number": "1.5", "title": "工程布置及主要建筑物", "writing_prompt": "简述工程等别和标准、坝（闸）址、坝（闸）型选择、工程总体布置、主要建筑物型式及尺寸、基础处理、机电及金属结构等。"},
            {"chapter_number": "1.6", "title": "施工组织设计", "writing_prompt": "简述施工条件、施工导流、主体工程施工、施工总布置、施工总进度等。"},
            {"chapter_number": "1.7", "title": "水库淹没与移民安置", "writing_prompt": "简述淹没范围、淹没实物指标、移民安置规划、专项设施改（迁）建等。"},
            {"chapter_number": "1.8", "title": "环境保护设计", "writing_prompt": "简述环境影响评价结论、主要不利影响减免措施、环境监测等。"},
            {"chapter_number": "1.9", "title": "水土保持设计", "writing_prompt": "简述水土流失防治责任范围、防治目标、防治措施及总体布局。"},
            {"chapter_number": "1.10", "title": "工程管理", "writing_prompt": "简述管理机构、管理范围、管理设施、管理运用等。"},
            {"chapter_number": "1.11", "title": "设计概算", "writing_prompt": "简述编制原则和依据、工程总投资、主要技术经济指标。"},
            {"chapter_number": "1.12", "title": "经济评价", "writing_prompt": "简述国民经济评价和财务评价成果、评价结论。"},
            {"chapter_number": "1.13", "title": "结论与建议", "writing_prompt": "综合说明工程的综合效益、技术可行性、经济合理性；提出下一阶段工作建议。"},
        ]
    },
    {
        "chapter_number": "2",
        "title": "水文",
        "level": 1,
        "sort_order": 2,
        "writing_prompt": "详细说明流域概况、气象、径流、洪水、泥沙、设计洪水等水文分析计算成果。",
        "required_params": ["catchment_area", "flood_std_design", "design_flow"],
        "reference_keywords": ["水文", "径流", "洪水", "设计洪水", "泥沙", "雨量站", "水文站"],
        "children": [
            {"chapter_number": "2.1", "title": "流域概况", "writing_prompt": "说明流域自然地理概况、河流水系、水利工程现状等。"},
            {"chapter_number": "2.2", "title": "气象", "writing_prompt": "说明流域及邻近地区气象台站分布与资料情况，主要气象要素特征值。"},
            {"chapter_number": "2.3", "title": "水文基本资料", "writing_prompt": "说明水文测站分布、资料测验情况、资料复核及评价。"},
            {"chapter_number": "2.4", "title": "径流", "writing_prompt": "说明径流系列的一致性、代表性分析，径流计算方法及成果，径流年内分配、年际变化。"},
            {"chapter_number": "2.5", "title": "洪水", "writing_prompt": "说明暴雨、洪水特性，历史洪水调查及考证，设计洪水计算方法及成果（洪峰、洪量、洪水过程线）。"},
            {"chapter_number": "2.6", "title": "泥沙", "writing_prompt": "说明泥沙来源、输沙量、含沙量特性，泥沙分析计算成果。"},
            {"chapter_number": "2.7", "title": "设计洪水", "writing_prompt": "说明工程场址设计洪水计算方法、采用的设计洪水成果及合理性检查。"},
        ]
    },
    {
        "chapter_number": "3",
        "title": "工程地质",
        "level": 1,
        "sort_order": 3,
        "writing_prompt": "详细说明区域地质、水库区地质、坝（闸）址工程地质条件、主要建筑物工程地质条件及评价结论和建议。",
        "reference_keywords": ["工程地质", "地质勘察", "区域地质", "水文地质", "岩土参数", "地质建议"],
        "children": [
            {"chapter_number": "3.1", "title": "区域地质", "writing_prompt": "说明地形地貌、地层岩性、地质构造、水文地质、物理地质现象等。"},
            {"chapter_number": "3.2", "title": "水库区工程地质条件", "writing_prompt": "说明水库渗漏、浸没、库岸稳定、库区淹没等工程地质问题评价。"},
            {"chapter_number": "3.3", "title": "坝（闸）址工程地质条件", "writing_prompt": "说明比较坝（闸）址的地形地貌、地层岩性、地质构造、水文地质条件、岩土物理力学性质等。"},
            {"chapter_number": "3.4", "title": "主要建筑物工程地质条件", "writing_prompt": "说明各主要建筑物地段的工程地质条件、存在的地质问题及处理建议。"},
            {"chapter_number": "3.5", "title": "天然建筑材料", "writing_prompt": "说明土料、砂砾料、石料等天然建筑材料的分布、储量、质量和开采运输条件。"},
            {"chapter_number": "3.6", "title": "结论与建议", "writing_prompt": "提出工程地质结论性意见和建议。"},
        ]
    },
    {
        "chapter_number": "4",
        "title": "工程任务和规模",
        "level": 1,
        "sort_order": 4,
        "writing_prompt": "说明区域经济发展规划、工程建设的必要性、工程开发任务、综合利用要求、水利计算、工程规模确定及特征水位选择。",
        "required_params": ["project_grade", "scale_type", "flood_std_design", "flood_std_check", "total_storage"],
        "reference_keywords": ["工程任务", "建设必要性", "工程规模", "水利计算", "特征水位", "防洪标准"],
        "children": [
            {"chapter_number": "4.1", "title": "地区社会经济概况及发展规划", "writing_prompt": "简述工程涉及地区社会经济现状、相关发展规划等。"},
            {"chapter_number": "4.2", "title": "工程建设的必要性", "writing_prompt": "从防洪安全、供水保障、粮食安全、能源需求、生态保护等方面论述工程建设的必要性。"},
            {"chapter_number": "4.3", "title": "工程开发任务", "writing_prompt": "确定工程开发任务和主次顺序。"},
            {"chapter_number": "4.4", "title": "防洪", "writing_prompt": "说明防洪保护对象、防洪标准、防洪库容、防洪调度运用方式。"},
            {"chapter_number": "4.5", "title": "供水与灌溉", "writing_prompt": "说明供水范围、供水保证率、用水量预测、灌溉面积、灌溉制度等。"},
            {"chapter_number": "4.6", "title": "发电", "writing_prompt": "说明供电范围、电力系统要求、装机容量选择、保证出力等。"},
            {"chapter_number": "4.7", "title": "工程规模", "writing_prompt": "通过水利计算和方案比较，确定工程规模及主要特征值。"},
        ]
    },
    {
        "chapter_number": "5",
        "title": "工程布置及建筑物",
        "level": 1,
        "sort_order": 5,
        "writing_prompt": "说明工程等别和标准、坝（闸）址和坝（闸）型选择、工程总体布置、主要建筑物设计、基础处理等。",
        "required_params": ["main_building_level", "secondary_building_level", "flood_std_design", "flood_std_check"],
        "reference_keywords": ["工程布置", "建筑物设计", "坝型选择", "闸型选择", "堤防设计", "消能防冲", "基础处理"],
        "children": [
            {"chapter_number": "5.1", "title": "设计依据", "writing_prompt": "列出设计采用的主要规程规范、工程等别及建筑物级别、设计基本资料等。"},
            {"chapter_number": "5.2", "title": "工程等别和建筑物级别", "writing_prompt": "确定工程等别、主要及次要建筑物级别、相应的洪水标准和安全加高。"},
            {"chapter_number": "5.3", "title": "坝（闸）址选择", "writing_prompt": "通过地形地质、枢纽布置、施工条件、工程量、投资等综合比较，选定坝（闸）址。"},
            {"chapter_number": "5.4", "title": "坝（闸）型选择", "writing_prompt": "对可能的坝（闸）型进行技术经济比较，选定推荐坝（闸）型。"},
            {"chapter_number": "5.5", "title": "工程总体布置", "writing_prompt": "说明各主要建筑物的位置、型式、尺寸及相互关系，进行方案比较选定总体布置方案。"},
            {"chapter_number": "5.6", "title": "挡水建筑物", "writing_prompt": "说明挡水建筑物的结构布置、断面设计、稳定计算、应力分析等。"},
            {"chapter_number": "5.7", "title": "泄水建筑物", "writing_prompt": "说明泄水建筑物的布置、型式、尺寸、泄流能力计算、消能防冲设计等。"},
            {"chapter_number": "5.8", "title": "输水建筑物", "writing_prompt": "说明输水建筑物（隧洞、涵管、渠道等）的线路选择、结构设计、水力计算等。"},
            {"chapter_number": "5.9", "title": "电站厂房及开关站", "writing_prompt": "说明厂房布置、结构设计、开关站布置等。"},
            {"chapter_number": "5.10", "title": "堤防工程", "writing_prompt": "说明堤线布置、堤型选择、堤身断面设计、堤岸防护设计等。"},
            {"chapter_number": "5.11", "title": "河道整治建筑物", "writing_prompt": "说明护岸、丁坝、顺坝等整治建筑物的布置和结构设计。"},
            {"chapter_number": "5.12", "title": "基础处理", "writing_prompt": "说明地基存在的问题、基础处理方案比选、处理措施设计。"},
            {"chapter_number": "5.13", "title": "主要建筑物工程量", "writing_prompt": "列出主要建筑物的主要工程量汇总表。"},
        ]
    },
    {
        "chapter_number": "6",
        "title": "机电及金属结构",
        "level": 1,
        "sort_order": 6,
        "writing_prompt": "说明水轮发电机组、电气主接线、金属结构等设备的选型、布置和主要参数。",
        "reference_keywords": ["水轮机", "发电机", "电气主接线", "闸门", "启闭机", "压力钢管"],
        "children": [
            {"chapter_number": "6.1", "title": "水力机械", "writing_prompt": "说明水轮发电机组型式、台数、单机容量、主要参数及辅助设备选择。"},
            {"chapter_number": "6.2", "title": "电气", "writing_prompt": "说明接入电力系统方式、电气主接线、主要电气设备选择、开关站布置等。"},
            {"chapter_number": "6.3", "title": "金属结构", "writing_prompt": "说明闸门、拦污栅、启闭机、压力钢管等金属结构的布置、型式、尺寸和主要参数。"},
        ]
    },
    {
        "chapter_number": "7",
        "title": "施工组织设计",
        "level": 1,
        "sort_order": 7,
        "writing_prompt": "说明施工条件、施工导流、主体工程施工方法、施工总布置、施工总进度等。",
        "required_params": ["construction_period"],
        "reference_keywords": ["施工导流", "主体工程施工", "施工总布置", "施工进度", "施工交通", "土石方平衡"],
        "children": [
            {"chapter_number": "7.1", "title": "施工条件", "writing_prompt": "说明工程条件、自然条件（水文、气象、地形地质）、交通运输条件、建材供应条件等。"},
            {"chapter_number": "7.2", "title": "施工导流", "writing_prompt": "说明导流标准、导流方式、导流建筑物设计、截流、基坑排水、施工期度汛等。"},
            {"chapter_number": "7.3", "title": "主体工程施工", "writing_prompt": "说明挡水、泄水、输水等主要建筑物的施工方法、施工程序、施工机械选择。"},
            {"chapter_number": "7.4", "title": "施工交通及施工总布置", "writing_prompt": "说明对外交通、场内交通规划；施工分区布置、风水电系统布置、弃渣场规划等。"},
            {"chapter_number": "7.5", "title": "施工总进度", "writing_prompt": "说明施工总工期、工程筹建期、准备期、主体工程施工期、工程完建期的安排，关键线路分析。"},
        ]
    },
    {
        "chapter_number": "8",
        "title": "水库淹没与移民安置",
        "level": 1,
        "sort_order": 8,
        "writing_prompt": "说明淹没处理范围、淹没实物指标调查、移民安置规划、专业项目处理、补偿投资概（估）算。",
        "reference_keywords": ["水库淹没", "移民安置", "淹没实物指标", "补偿投资"],
        "children": [
            {"chapter_number": "8.1", "title": "淹没处理范围", "writing_prompt": "确定水库淹没处理范围和浸没、坍岸、滑坡影响范围。"},
            {"chapter_number": "8.2", "title": "淹没实物指标", "writing_prompt": "说明淹没影响的人口、房屋、土地、专项设施等实物指标调查成果。"},
            {"chapter_number": "8.3", "title": "移民安置规划", "writing_prompt": "说明移民安置去向、安置区环境容量分析、生产安置规划、搬迁安置规划。"},
            {"chapter_number": "8.4", "title": "专业项目处理", "writing_prompt": "说明铁路、公路、电力、通信、水利设施等专业项目的改（迁）建规划。"},
        ]
    },
    {
        "chapter_number": "9",
        "title": "环境保护设计",
        "level": 1,
        "sort_order": 9,
        "writing_prompt": "说明环境影响评价结论、主要不利影响的减免措施、环境监测与管理、环境保护投资概算。",
        "reference_keywords": ["环境保护", "环境影响", "水质保护", "生态保护", "环境监测"],
        "children": [
            {"chapter_number": "9.1", "title": "环境影响评价结论", "writing_prompt": "简述环境影响报告书的主要结论。"},
            {"chapter_number": "9.2", "title": "环境保护设计", "writing_prompt": "针对工程对环境的不利影响，提出相应的减免措施设计。"},
            {"chapter_number": "9.3", "title": "环境监测与管理", "writing_prompt": "提出施工期和运行期环境监测规划、环境管理要求。"},
        ]
    },
    {
        "chapter_number": "10",
        "title": "水土保持设计",
        "level": 1,
        "sort_order": 10,
        "writing_prompt": "说明水土流失防治责任范围、水土流失预测、防治目标、防治措施总体布局和设计、水土保持监测。",
        "reference_keywords": ["水土保持", "水土流失", "防治分区", "工程措施", "植物措施", "临时措施", "土石方平衡"],
        "children": [
            {"chapter_number": "10.1", "title": "水土流失防治责任范围", "writing_prompt": "确定项目建设区和直接影响区范围。"},
            {"chapter_number": "10.2", "title": "水土流失预测", "writing_prompt": "预测工程建设可能造成的水土流失量和危害。"},
            {"chapter_number": "10.3", "title": "防治目标及措施总体布局", "writing_prompt": "确定防治标准、防治分区、措施体系和总体布局。"},
            {"chapter_number": "10.4", "title": "分区措施设计", "writing_prompt": "说明各防治区的工程措施、植物措施、临时措施设计。"},
            {"chapter_number": "10.5", "title": "水土保持监测", "writing_prompt": "提出监测范围、监测内容、监测时段和监测点位布设。"},
        ]
    },
    {
        "chapter_number": "11",
        "title": "工程管理",
        "level": 1,
        "sort_order": 11,
        "writing_prompt": "说明管理机构、管理范围和保护范围、管理设施、工程运用调度、管理用房及人员编制等。",
        "reference_keywords": ["工程管理", "管理机构", "管理范围", "调度运用", "管理设施"],
        "children": [
            {"chapter_number": "11.1", "title": "管理机构", "writing_prompt": "确定管理机构设置、人员编制。"},
            {"chapter_number": "11.2", "title": "管理范围和保护范围", "writing_prompt": "划定工程管理范围和保护范围。"},
            {"chapter_number": "11.3", "title": "工程运用调度", "writing_prompt": "提出工程调度运用方案。"},
            {"chapter_number": "11.4", "title": "管理设施", "writing_prompt": "说明管理用房、观测设施、通信设施、交通设施等管理设施设计。"},
        ]
    },
    {
        "chapter_number": "12",
        "title": "设计概算",
        "level": 1,
        "sort_order": 12,
        "writing_prompt": "说明编制原则和依据、基础价格、建筑及安装工程单价、各部分概算编制、总概算及主要技术经济指标。",
        "required_params": ["total_investment"],
        "reference_keywords": ["设计概算", "编制依据", "工程单价", "总投资", "工程量清单", "技术经济指标"],
        "children": [
            {"chapter_number": "12.1", "title": "编制原则和依据", "writing_prompt": "说明概算编制的原则、依据、定额、费用标准等。"},
            {"chapter_number": "12.2", "title": "基础价格", "writing_prompt": "说明人工预算单价、材料预算价格、电水风价格、施工机械台时费等基础单价计算。"},
            {"chapter_number": "12.3", "title": "建筑及安装工程单价", "writing_prompt": "说明主要建筑及安装工程单价的编制。"},
            {"chapter_number": "12.4", "title": "概算编制", "writing_prompt": "编制建筑工程、机电设备及安装、金属结构设备及安装、临时工程、独立费用等各部分概算。"},
            {"chapter_number": "12.5", "title": "总概算及主要技术经济指标", "writing_prompt": "编制工程总概算表，分析主要技术经济指标。"},
        ]
    },
    {
        "chapter_number": "13",
        "title": "经济评价",
        "level": 1,
        "sort_order": 13,
        "writing_prompt": "说明国民经济评价、财务评价的方法、参数、费用效益计算及评价结论。",
        "reference_keywords": ["经济评价", "国民经济评价", "财务评价", "效益费用比", "经济内部收益率"],
        "children": [
            {"chapter_number": "13.1", "title": "国民经济评价", "writing_prompt": "说明费用计算、效益计算、国民经济评价指标计算及敏感性分析。"},
            {"chapter_number": "13.2", "title": "财务评价", "writing_prompt": "说明财务支出、财务收入、财务评价指标计算、清偿能力分析。"},
            {"chapter_number": "13.3", "title": "评价结论", "writing_prompt": "综合国民经济评价和财务评价，提出评价结论。"},
        ]
    },
]

# 可研报告简化章节（参考）
FEASIBILITY_CHAPTERS = [
    {"chapter_number": "1", "title": "综合说明", "level": 1, "sort_order": 1},
    {"chapter_number": "2", "title": "水文", "level": 1, "sort_order": 2},
    {"chapter_number": "3", "title": "工程地质", "level": 1, "sort_order": 3},
    {"chapter_number": "4", "title": "工程任务和规模", "level": 1, "sort_order": 4},
    {"chapter_number": "5", "title": "工程选址及总体布置", "level": 1, "sort_order": 5},
    {"chapter_number": "6", "title": "主要建筑物", "level": 1, "sort_order": 6},
    {"chapter_number": "7", "title": "机电及金属结构", "level": 1, "sort_order": 7},
    {"chapter_number": "8", "title": "施工组织设计", "level": 1, "sort_order": 8},
    {"chapter_number": "9", "title": "水库淹没与移民安置", "level": 1, "sort_order": 9},
    {"chapter_number": "10", "title": "环境影响评价", "level": 1, "sort_order": 10},
    {"chapter_number": "11", "title": "水土保持", "level": 1, "sort_order": 11},
    {"chapter_number": "12", "title": "工程管理", "level": 1, "sort_order": 12},
    {"chapter_number": "13", "title": "投资估算", "level": 1, "sort_order": 13},
    {"chapter_number": "14", "title": "经济评价", "level": 1, "sort_order": 14},
    {"chapter_number": "15", "title": "结论与建议", "level": 1, "sort_order": 15},
]


def _add_chapters_recursive(db: Session, chapters: list, parent_id: int = None, project_types: list = None, stages: list = None):
    """递归添加章节"""
    for ch_data in chapters:
        children = ch_data.get("children", [])
        
        tpl = ReportSectionTemplate(
            chapter_number=ch_data["chapter_number"],
            title=ch_data["title"],
            parent_id=parent_id,
            level=ch_data.get("level", 1),
            applicable_project_types=project_types,
            applicable_stages=stages,
            writing_prompt=ch_data.get("writing_prompt", ""),
            required_params=ch_data.get("required_params", []),
            reference_keywords=ch_data.get("reference_keywords", []),
            sort_order=ch_data.get("sort_order", 0),
            is_active=True
        )
        db.add(tpl)
        db.flush()
        
        if children:
            _add_chapters_recursive(db, children, parent_id=tpl.id, project_types=project_types, stages=stages)


def seed_section_templates(db: Session):
    """Seed章节模板"""
    existing_count = db.query(ReportSectionTemplate).count()
    if existing_count > 0:
        print(f"章节模板已存在({existing_count}个)，跳过seed")
        return
    
    all_types = ["river_training", "reservoir_reinforcement", "drainage_pump", "mountain_flood", "dike_engineering", "sluice_culvert"]
    
    # 初步设计章节
    _add_chapters_recursive(
        db, 
        PRELIMINARY_DESIGN_CHAPTERS, 
        parent_id=None,
        project_types=all_types,
        stages=["preliminary", "construction"]
    )
    
    # 可研章节
    # _add_chapters_recursive(db, FEASIBILITY_CHAPTERS, parent_id=None, project_types=all_types, stages=["feasibility"])
    
    db.commit()
    total = db.query(ReportSectionTemplate).count()
    print(f"章节模板seed完成: {total}个章节")
