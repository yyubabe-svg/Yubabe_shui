"""表单模板Seed数据 - 工程特性表、质量认证表等"""
from sqlalchemy.orm import Session
from app.models.form_template import (
    FormTemplate, FormField, FormTemplateType, FormFieldType
)


# 工程特性表字段定义
PROJECT_FEATURE_FIELDS = [
    {"field_key": "project_name", "field_label": "工程名称", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 1,
     "llm_extract_hint": "项目/工程的完整名称，通常在报告封面或项目概况中"},
    {"field_key": "project_location", "field_label": "工程位置", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 2,
     "llm_extract_hint": "工程所在的省、市、县、乡镇，具体地理位置描述"},
    {"field_key": "river_basin", "field_label": "所属流域/河流", "field_type": FormFieldType.TEXT.value, "required": False, "sort_order": 3,
     "llm_extract_hint": "工程所属的流域名称，如长江流域、岷江流域，或所在河道名称"},
    {"field_key": "project_grade", "field_label": "工程等别", "field_type": FormFieldType.SELECT.value, "required": True, "sort_order": 4,
     "options_json": [{"value": "Ⅰ", "label": "Ⅰ等"}, {"value": "Ⅱ", "label": "Ⅱ等"}, {"value": "Ⅲ", "label": "Ⅲ等"}, {"value": "Ⅳ", "label": "Ⅳ等"}, {"value": "Ⅴ", "label": "Ⅴ等"}],
     "llm_extract_hint": "水利水电工程等别，根据《水利水电工程等级划分及洪水标准》SL252确定，为Ⅰ/Ⅱ/Ⅲ/Ⅳ/Ⅴ等"},
    {"field_key": "scale_type", "field_label": "工程规模", "field_type": FormFieldType.SELECT.value, "required": True, "sort_order": 5,
     "options_json": [{"value": "大(1)型", "label": "大(1)型"}, {"value": "大(2)型", "label": "大(2)型"}, {"value": "中型", "label": "中型"}, {"value": "小(1)型", "label": "小(1)型"}, {"value": "小(2)型", "label": "小(2)型"}],
     "llm_extract_hint": "工程规模：大(1)型、大(2)型、中型、小(1)型、小(2)型"},
    {"field_key": "main_building_level", "field_label": "主要建筑物级别", "field_type": FormFieldType.SELECT.value, "required": True, "sort_order": 6,
     "options_json": [{"value": "1", "label": "1级"}, {"value": "2", "label": "2级"}, {"value": "3", "label": "3级"}, {"value": "4", "label": "4级"}, {"value": "5", "label": "5级"}],
     "llm_extract_hint": "主要建筑物级别，根据工程等别确定，1-5级"},
    {"field_key": "secondary_building_level", "field_label": "次要建筑物级别", "field_type": FormFieldType.SELECT.value, "required": False, "sort_order": 7,
     "options_json": [{"value": "2", "label": "2级"}, {"value": "3", "label": "3级"}, {"value": "4", "label": "4级"}, {"value": "5", "label": "5级"}],
     "llm_extract_hint": "次要建筑物级别，通常比主要建筑物低一级"},
    {"field_key": "flood_std_design", "field_label": "设计防洪标准", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 8,
     "llm_extract_hint": "设计洪水标准，如'20年一遇'、'50年一遇'、'100年一遇'"},
    {"field_key": "flood_std_check", "field_label": "校核防洪标准", "field_type": FormFieldType.TEXT.value, "required": False, "sort_order": 9,
     "llm_extract_hint": "校核洪水标准，如'100年一遇'、'200年一遇'、'1000年一遇'"},
    {"field_key": "seismic_intensity", "field_label": "地震设防烈度", "field_type": FormFieldType.TEXT.value, "required": False, "sort_order": 10,
     "llm_extract_hint": "地震基本烈度/设防烈度，如'Ⅶ度'、'Ⅷ度'"},
    {"field_key": "catchment_area", "field_label": "集水/流域面积(km²)", "field_type": FormFieldType.NUMBER.value, "required": False, "sort_order": 11,
     "llm_extract_hint": "坝址/工程位置以上的集水面积或流域面积，单位平方公里(km²)，提取数字"},
    {"field_key": "river_governance_length", "field_label": "治理河长(km)", "field_type": FormFieldType.NUMBER.value, "required": False, "sort_order": 12,
     "llm_extract_hint": "本次工程治理的河道总长度，单位公里(km)，提取数字"},
    {"field_key": "embankment_length", "field_label": "堤防长度(km)", "field_type": FormFieldType.NUMBER.value, "required": False, "sort_order": 13,
     "llm_extract_hint": "新建或加固堤防的总长度，单位公里(km)，提取数字"},
    {"field_key": "design_flow", "field_label": "设计流量(m³/s)", "field_type": FormFieldType.NUMBER.value, "required": False, "sort_order": 14,
     "llm_extract_hint": "设计洪水流量或设计排涝流量，单位立方米每秒(m³/s)"},
    {"field_key": "total_storage", "field_label": "总库容(万m³)", "field_type": FormFieldType.NUMBER.value, "required": False, "sort_order": 15,
     "llm_extract_hint": "水库总库容，单位万立方米(万m³)"},
    {"field_key": "total_investment", "field_label": "工程总投资(万元)", "field_type": FormFieldType.NUMBER.value, "required": True, "sort_order": 16,
     "llm_extract_hint": "工程概算总投资，单位万元，提取数字"},
    {"field_key": "construction_period", "field_label": "施工总工期(月)", "field_type": FormFieldType.NUMBER.value, "required": False, "sort_order": 17,
     "llm_extract_hint": "工程施工总工期，单位月，提取数字"},
    {"field_key": "client", "field_label": "建设单位", "field_type": FormFieldType.TEXT.value, "required": False, "sort_order": 18,
     "llm_extract_hint": "项目法人/建设单位名称"},
    {"field_key": "designer", "field_label": "设计负责人", "field_type": FormFieldType.TEXT.value, "required": False, "sort_order": 19,
     "llm_extract_hint": "设计负责人姓名，通常在报告封面或设计人员页"},
    {"field_key": "report_date", "field_label": "报告编制日期", "field_type": FormFieldType.DATE.value, "required": False, "sort_order": 20,
     "llm_extract_hint": "报告编制完成日期，如'2024年6月'"},
]

# 质量认证表字段定义
QUALITY_FIELDS = [
    {"field_key": "project_name", "field_label": "工程名称", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 1,
     "llm_extract_hint": "项目/工程的完整名称"},
    {"field_key": "design_unit", "field_label": "设计单位", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 2,
     "llm_extract_hint": "设计院名称，如'XX市水利电力勘测设计院'"},
    {"field_key": "client", "field_label": "委托单位/建设单位", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 3,
     "llm_extract_hint": "项目委托方或建设单位名称"},
    {"field_key": "design_stage", "field_label": "设计阶段", "field_type": FormFieldType.SELECT.value, "required": True, "sort_order": 4,
     "options_json": [{"value": "项目建议书", "label": "项目建议书"}, {"value": "可行性研究", "label": "可行性研究"}, {"value": "初步设计", "label": "初步设计"}, {"value": "施工图设计", "label": "施工图设计"}],
     "llm_extract_hint": "设计阶段：项目建议书、可行性研究、初步设计、施工图设计"},
    {"field_key": "design_director", "field_label": "设计总负责人", "field_type": FormFieldType.TEXT.value, "required": False, "sort_order": 5},
    {"field_key": "designer", "field_label": "设计负责人", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 6,
     "llm_extract_hint": "设计负责人姓名"},
    {"field_key": "checker", "field_label": "校核人", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 7,
     "llm_extract_hint": "校核人姓名"},
    {"field_key": "reviewer", "field_label": "审核人", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 8,
     "llm_extract_hint": "审核人/室审人姓名"},
    {"field_key": "approver", "field_label": "审定人", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 9,
     "llm_extract_hint": "审定人/总工姓名"},
    {"field_key": "department", "field_label": "设计部门", "field_type": FormFieldType.TEXT.value, "required": False, "sort_order": 10,
     "llm_extract_hint": "承担设计的科室/部门名称"},
    {"field_key": "report_date", "field_label": "完成日期", "field_type": FormFieldType.DATE.value, "required": True, "sort_order": 11,
     "llm_extract_hint": "设计文件完成日期"},
    {"field_key": "project_number", "field_label": "项目编号", "field_type": FormFieldType.TEXT.value, "required": False, "sort_order": 12,
     "llm_extract_hint": "设计院内部项目编号"},
]

# 设计输入输出表字段定义
DESIGN_IO_FIELDS = [
    {"field_key": "project_name", "field_label": "工程名称", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 1},
    {"field_key": "design_stage", "field_label": "设计阶段", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 2},
    {"field_key": "input_documents", "field_label": "输入资料清单", "field_type": FormFieldType.TEXTAREA.value, "required": True, "sort_order": 3,
     "llm_extract_hint": "设计依据和输入资料清单，包括批复文件、地勘报告、测量资料、水文资料等"},
    {"field_key": "output_documents", "field_label": "输出成果清单", "field_type": FormFieldType.TEXTAREA.value, "required": True, "sort_order": 4,
     "llm_extract_hint": "本次设计交付的成果清单，包括设计报告、图纸、计算书等"},
    {"field_key": "applicable_standards", "field_label": "采用规范标准", "field_type": FormFieldType.TEXTAREA.value, "required": True, "sort_order": 5,
     "llm_extract_hint": "本项目采用的主要国家/行业/地方规范标准清单"},
    {"field_key": "designer", "field_label": "设计人", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 6},
    {"field_key": "checker", "field_label": "校核人", "field_type": FormFieldType.TEXT.value, "required": True, "sort_order": 7},
    {"field_key": "date", "field_label": "日期", "field_type": FormFieldType.DATE.value, "required": True, "sort_order": 8},
]


def seed_form_templates(db: Session):
    """Seed表单模板"""
    # 检查是否已有模板
    existing_count = db.query(FormTemplate).count()
    if existing_count > 0:
        print(f"表单模板已存在({existing_count}个)，跳过seed")
        return
    
    # 适用项目类型
    all_types = ["river_training", "reservoir_reinforcement", "drainage_pump", "mountain_flood", "irrigation_upgrade", "soil_conservation", "flood_evaluation", "rural_water", "urban_waterlogging", "dike_engineering", "sluice_culvert", "water_resource", "small_farmland_water"]
    
    templates = [
        {
            "template_code": "PROJECT_FEATURE_01",
            "template_name": "工程特性表",
            "template_type": FormTemplateType.PROJECT_FEATURE.value,
            "applicable_project_types": all_types,
            "description": "水利水电工程特性表，包含项目基本信息、工程等级、防洪标准、主要技术经济指标",
            "sort_order": 1,
            "fields": PROJECT_FEATURE_FIELDS
        },
        {
            "template_code": "QUALITY_01",
            "template_name": "设计质量认证表",
            "template_type": FormTemplateType.QUALITY.value,
            "applicable_project_types": all_types,
            "description": "ISO质量管理体系设计文件校审签署表",
            "sort_order": 2,
            "fields": QUALITY_FIELDS
        },
        {
            "template_code": "DESIGN_IO_01",
            "template_name": "设计输入输出清单",
            "template_type": FormTemplateType.OTHER.value,
            "applicable_project_types": all_types,
            "description": "设计输入资料清单和输出成果清单",
            "sort_order": 3,
            "fields": DESIGN_IO_FIELDS
        },
    ]
    
    for tpl_data in templates:
        fields_data = tpl_data.pop("fields")
        tpl = FormTemplate(**tpl_data)
        db.add(tpl)
        db.flush()  # 获取id
        
        for f_data in fields_data:
            field = FormField(template_id=tpl.id, **f_data)
            db.add(field)
    
    db.commit()
    print(f"表单模板seed完成: {len(templates)}个模板")
