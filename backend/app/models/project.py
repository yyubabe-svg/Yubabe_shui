import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProjectType(str, enum.Enum):
    """项目类型枚举"""
    RIVER_TRAINING = "river_training"          # 河道治理
    RESERVOIR_REINFORCEMENT = "reservoir_reinforcement"  # 水库除险加固
    DRAINAGE_PUMP = "drainage_pump"            # 排涝泵站
    MOUNTAIN_FLOOD = "mountain_flood"          # 山洪沟治理
    IRRIGATION_UPGRADE = "irrigation_upgrade"  # 灌区改造
    SOIL_CONSERVATION = "soil_conservation"    # 水土保持
    FLOOD_EVALUATION = "flood_evaluation"      # 防洪评价
    RURAL_WATER = "rural_water"                # 农村供水
    URBAN_WATERLOGGING = "urban_waterlogging"  # 城市内涝
    DIKE_ENGINEERING = "dike_engineering"      # 堤防工程
    SLUICE_CULVERT = "sluice_culvert"          # 涵闸工程
    WATER_RESOURCE = "water_resource"          # 水资源论证
    SMALL_FARMLAND_WATER = "small_farmland_water"  # 小型农田水利


class DesignStage(str, enum.Enum):
    """设计阶段枚举"""
    PROPOSAL = "proposal"              # 项目建议书
    FEASIBILITY = "feasibility"        # 可行性研究
    PRELIMINARY = "preliminary"        # 初步设计
    IMPLEMENTATION = "implementation"  # 实施方案
    CONSTRUCTION = "construction"      # 施工图


class ProjectStatus(str, enum.Enum):
    """项目状态枚举"""
    ACTIVE = "active"
    ARCHIVED = "archived"


# 项目类型中文名称映射
PROJECT_TYPE_NAMES = {
    ProjectType.RIVER_TRAINING: "河道治理",
    ProjectType.RESERVOIR_REINFORCEMENT: "水库除险加固",
    ProjectType.DRAINAGE_PUMP: "排涝泵站",
    ProjectType.MOUNTAIN_FLOOD: "山洪沟治理",
    ProjectType.IRRIGATION_UPGRADE: "灌区改造",
    ProjectType.SOIL_CONSERVATION: "水土保持",
    ProjectType.FLOOD_EVALUATION: "防洪评价",
    ProjectType.RURAL_WATER: "农村供水",
    ProjectType.URBAN_WATERLOGGING: "城市内涝",
    ProjectType.DIKE_ENGINEERING: "堤防工程",
    ProjectType.SLUICE_CULVERT: "涵闸工程",
    ProjectType.WATER_RESOURCE: "水资源论证",
    ProjectType.SMALL_FARMLAND_WATER: "小型农田水利",
}

# 设计阶段中文名称映射
DESIGN_STAGE_NAMES = {
    DesignStage.PROPOSAL: "项目建议书",
    DesignStage.FEASIBILITY: "可行性研究",
    DesignStage.PRELIMINARY: "初步设计",
    DesignStage.IMPLEMENTATION: "实施方案",
    DesignStage.CONSTRUCTION: "施工图",
}


class DesignProject(Base):
    """设计项目 - 所有模块的关联中心"""
    __tablename__ = "design_projects"

    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(50), unique=True, index=True)
    project_name = Column(String(500), nullable=False)
    project_type = Column(String(50), nullable=False, index=True)
    design_stage = Column(String(30))
    
    # 项目参与方
    client = Column(String(200))           # 建设单位
    designer = Column(String(100))         # 设计负责人
    department = Column(String(100))       # 设计部门
    location = Column(String(200))         # 项目位置
    river_basin = Column(String(100))      # 所属流域/河流
    
    # 核心工程参数（从报告自动提取）
    project_grade = Column(String(10))           # 工程等别 Ⅰ/Ⅱ/Ⅲ/Ⅳ/Ⅴ
    scale_type = Column(String(20))              # 工程规模 大(1)型/大(2)型/中型/小(1)型/小(2)型
    main_building_level = Column(Integer)        # 主要建筑物级别 1-5
    secondary_building_level = Column(Integer)   # 次要建筑物级别
    temporary_building_level = Column(Integer)   # 临时建筑物级别
    flood_std_design = Column(String(50))        # 设计防洪标准
    flood_std_check = Column(String(50))         # 校核防洪标准
    drainage_std = Column(String(50))            # 排涝标准
    seismic_intensity = Column(String(20))       # 地震烈度
    seismic_peak_acc = Column(String(20))        # 地震动峰值加速度
    
    # 水文气象
    avg_annual_rainfall = Column(Float)          # 多年平均降雨量(mm)
    design_flood_flow = Column(Float)            # 设计洪峰流量(m³/s)
    check_flood_flow = Column(Float)             # 校核洪峰流量(m³/s)
    design_flood_level = Column(Float)           # 设计洪水位(m)
    check_flood_level = Column(Float)            # 校核洪水位(m)
    normal_water_level = Column(Float)           # 正常蓄水位(m)
    dead_water_level = Column(Float)             # 死水位(m)
    flood_return_period = Column(Integer)        # 设计洪水重现期(年)
    catchment_area = Column(Float)               # 集水面积(km²)
    
    # 工程规模指标
    storage_capacity = Column(Float)             # 总库容(万m³)
    dead_storage = Column(Float)                 # 死库容(万m³)
    embankment_length = Column(Float)            # 堤防总长度(km)
    embankment_height_max = Column(Float)        # 最大堤高(m)
    river_governance_length = Column(Float)      # 治理河长(km)
    dredging_length = Column(Float)              # 清淤长度(km)
    dredging_volume = Column(Float)              # 清淤量(万m³)
    protect_population = Column(Float)           # 保护人口(万人)
    protect_farmland = Column(Float)             # 保护耕地(万亩)
    irrigation_area = Column(Float)              # 灌溉面积(万亩)
    improved_irrigation_area = Column(Float)     # 改善灌溉面积(万亩)
    installed_capacity = Column(Float)           # 装机容量(kW)
    pump_design_flow = Column(Float)             # 设计流量(m³/s)
    pump_head = Column(Float)                    # 设计扬程(m)
    water_supply_population = Column(Float)      # 供水人口(万人)
    
    # 主要建筑物
    dam_type = Column(String(50))                # 坝型
    dam_height_max = Column(Float)               # 最大坝高(m)
    dam_crest_width = Column(Float)              # 坝顶宽度(m)
    dam_crest_elevation = Column(Float)          # 坝顶高程(m)
    spillway_type = Column(String(100))          # 溢洪道型式
    sluice_gate_count = Column(Integer)          # 闸门数量
    dam_crest_freeboard = Column(Float)          # 坝顶超高(m)
    levee_crest_width = Column(Float)            # 堤顶宽度(m)
    levee_crest_freeboard = Column(Float)        # 堤顶超高(m)
    
    # 施工与投资
    construction_period = Column(Integer)        # 施工总工期(月)
    total_earthwork = Column(Float)              # 总土方(万m³)
    total_concrete = Column(Float)               # 总混凝土(万m³)
    total_masonry = Column(Float)                # 总砌石(万m³)
    land_acquisition = Column(Float)             # 工程占地(亩)
    resettlement = Column(Integer)               # 移民安置(人)
    total_investment = Column(Float)             # 工程总投资(万元)
    construction_cost = Column(Float)            # 建筑工程投资(万元)
    
    # 生态水保
    soil_loss_area = Column(Float)               # 水土流失面积(km²)
    env_investment = Column(Float)               # 环保投资(万元)
    wb_investment = Column(Float)                # 水保投资(万元)
    ecological_flow = Column(Float)              # 生态流量(m³/s)
    
    # 元数据
    status = Column(String(30), default=ProjectStatus.ACTIVE.value)
    report_file_id = Column(Integer, ForeignKey("documents.id"))
    extracted_fields_json = Column(JSON)         # LLM提取的完整字段字典
    applicable_codes_json = Column(JSON)         # 适用规范清单
    involved_majors_json = Column(JSON)          # 涉及专业列表
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    report_file = relationship("Document", foreign_keys=[report_file_id])
    documents = relationship("Document", back_populates="project", foreign_keys="Document.project_id", cascade="all, delete-orphan")
    form_tasks = relationship("FormFillTask", back_populates="project", cascade="all, delete-orphan")
    section_tasks = relationship("ReportSectionTask", back_populates="project", cascade="all, delete-orphan")
    review_tasks = relationship("AIReviewTask", back_populates="project", cascade="all, delete-orphan")
    expert_reply_tasks = relationship("ExpertReplyTask", back_populates="project", cascade="all, delete-orphan")

    @property
    def project_type_name(self):
        """项目类型中文名称"""
        try:
            return PROJECT_TYPE_NAMES[ProjectType(self.project_type)]
        except (ValueError, KeyError):
            return self.project_type

    @property
    def design_stage_name(self):
        """设计阶段中文名称"""
        try:
            return DESIGN_STAGE_NAMES[DesignStage(self.design_stage)]
        except (ValueError, KeyError):
            return self.design_stage
