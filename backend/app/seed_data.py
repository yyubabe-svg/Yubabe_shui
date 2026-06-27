"""Mock数据初始化 - 初始化示例文档数据和示例项目"""
from sqlalchemy.orm import Session
from app.models.document import Document, FileType, SecurityLevel, ParseStatus
from app.models.project import DesignProject, ProjectType, DesignStage, ProjectStatus
from app.models.user_usage import UserUsage


def init_mock_data(db: Session):
    """初始化Mock数据"""
    # 检查是否已有文档数据
    doc_count = db.query(Document).count()
    project_count = db.query(DesignProject).count()
    
    # 创建示例文档（规范）
    if doc_count == 0:
        sample_docs = [
            {
                "title": "《防洪标准》GB 50201-2014",
                "file_type": FileType.STANDARD.value,
                "security_level": SecurityLevel.PUBLIC.value,
                "parse_status": ParseStatus.COMPLETED.value,
                "file_path": "",
                "chunk_count": 0,
            },
            {
                "title": "《水利水电工程等级划分及洪水标准》SL 252-2017",
                "file_type": FileType.STANDARD.value,
                "security_level": SecurityLevel.PUBLIC.value,
                "parse_status": ParseStatus.COMPLETED.value,
                "file_path": "",
                "chunk_count": 0,
            },
            {
                "title": "《堤防工程设计规范》GB 50286-2013",
                "file_type": FileType.STANDARD.value,
                "security_level": SecurityLevel.PUBLIC.value,
                "parse_status": ParseStatus.COMPLETED.value,
                "file_path": "",
                "chunk_count": 0,
            },
            {
                "title": "《水利水电工程初步设计报告编制规程》SL/T 619-2021",
                "file_type": FileType.STANDARD.value,
                "security_level": SecurityLevel.PUBLIC.value,
                "parse_status": ParseStatus.COMPLETED.value,
                "file_path": "",
                "chunk_count": 0,
            },
            {
                "title": "《小型水利水电工程碾压式土石坝设计规范》SL 189-2013",
                "file_type": FileType.STANDARD.value,
                "security_level": SecurityLevel.PUBLIC.value,
                "parse_status": ParseStatus.COMPLETED.value,
                "file_path": "",
                "chunk_count": 0,
            },
            {
                "title": "《灌溉与排水工程设计标准》GB 50288-2018",
                "file_type": FileType.STANDARD.value,
                "security_level": SecurityLevel.PUBLIC.value,
                "parse_status": ParseStatus.COMPLETED.value,
                "file_path": "",
                "chunk_count": 0,
            },
            {
                "title": "《开发建设项目水土保持技术规范》GB 50433-2018",
                "file_type": FileType.STANDARD.value,
                "security_level": SecurityLevel.PUBLIC.value,
                "parse_status": ParseStatus.COMPLETED.value,
                "file_path": "",
                "chunk_count": 0,
            },
        ]
        
        for d in sample_docs:
            doc = Document(**d)
            db.add(doc)
        
        db.commit()
        print(f"Mock规范文档初始化完成: {len(sample_docs)}个")
    
    # 创建示例项目
    if project_count == 0:
        sample_projects = [
            {
                "project_code": "PRJ-DEMO-001",
                "project_name": "大渡河左岸乐山市金口河区滨河路堤防工程初步设计",
                "project_type": ProjectType.RIVER_TRAINING.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "乐山市金口河区水务局",
                "designer": "张工",
                "department": "水工设计室",
                "location": "四川省乐山市金口河区",
                "river_basin": "长江流域-大渡河水系",
                "project_grade": "Ⅳ",
                "scale_type": "小(1)型",
                "main_building_level": 4,
                "flood_std_design": "20年一遇",
                "flood_std_check": "50年一遇",
                "catchment_area": 68.5,
                "river_governance_length": 3.2,
                "embankment_length": 2.8,
                "total_investment": 5860,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-DEMO-002",
                "project_name": "新津安西镇月花村秦大沟综合治理项目可行性研究",
                "project_type": ProjectType.RIVER_TRAINING.value,
                "design_stage": DesignStage.FEASIBILITY.value,
                "client": "成都市新津区水务局",
                "designer": "李工",
                "department": "规划室",
                "location": "四川省成都市新津区安西镇",
                "river_basin": "长江流域-岷江水系",
                "project_grade": "Ⅴ",
                "scale_type": "小(2)型",
                "main_building_level": 5,
                "flood_std_design": "10年一遇",
                "catchment_area": 12.3,
                "river_governance_length": 2.5,
                "embankment_length": 1.8,
                "total_investment": 2180,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-DEMO-003",
                "project_name": "眉山市东坡区红光水库除险加固工程初步设计",
                "project_type": ProjectType.RESERVOIR_REINFORCEMENT.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "眉山市东坡区水利局",
                "designer": "王工",
                "department": "水工设计室",
                "location": "四川省眉山市东坡区",
                "river_basin": "长江流域-岷江支流",
                "project_grade": "Ⅴ",
                "scale_type": "小(2)型水库",
                "main_building_level": 5,
                "flood_std_design": "20年一遇",
                "flood_std_check": "200年一遇",
                "catchment_area": 5.8,
                "total_investment": 1250,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-DEMO-004",
                "project_name": "德阳市旌阳区天元排涝泵站工程初步设计",
                "project_type": ProjectType.DRAINAGE_PUMP.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "德阳市旌阳区住房和城乡建设局",
                "designer": "刘工",
                "department": "市政给排水室",
                "location": "四川省德阳市旌阳区",
                "river_basin": "长江流域-沱江水系",
                "project_grade": "Ⅳ",
                "scale_type": "中型泵站",
                "main_building_level": 4,
                "flood_std_design": "20年一遇",
                "total_investment": 3420,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            # ===== 以下为已完成历史项目（用于历史复用推荐） =====
            {
                "project_code": "PRJ-HIS-001",
                "project_name": "青衣江雅安段防洪治理工程初步设计",
                "project_type": ProjectType.RIVER_TRAINING.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "雅安市水利局",
                "designer": "张工",
                "department": "河道设计室",
                "location": "四川省雅安市雨城区",
                "river_basin": "长江流域-青衣江水系",
                "project_grade": "Ⅲ",
                "scale_type": "中型",
                "main_building_level": 3,
                "flood_std_design": "30年一遇",
                "flood_std_check": "100年一遇",
                "catchment_area": 320.0,
                "river_governance_length": 12.5,
                "embankment_length": 10.8,
                "total_investment": 18500,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-HIS-002",
                "project_name": "绵阳涪城区青义堤防工程施工图设计",
                "project_type": ProjectType.RIVER_TRAINING.value,
                "design_stage": DesignStage.CONSTRUCTION.value,
                "client": "绵阳市涪城区水务局",
                "designer": "陈工",
                "department": "河道设计室",
                "location": "四川省绵阳市涪城区",
                "river_basin": "长江流域-涪江水系",
                "project_grade": "Ⅳ",
                "scale_type": "小(1)型",
                "main_building_level": 4,
                "flood_std_design": "20年一遇",
                "flood_std_check": "50年一遇",
                "catchment_area": 85.0,
                "river_governance_length": 5.6,
                "embankment_length": 4.8,
                "total_investment": 7200,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-HIS-003",
                "project_name": "乐山市市中区剑峰水库除险加固工程初步设计",
                "project_type": ProjectType.RESERVOIR_REINFORCEMENT.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "乐山市市中区水务局",
                "designer": "王工",
                "department": "水工设计室",
                "location": "四川省乐山市市中区",
                "river_basin": "长江流域-岷江支流",
                "project_grade": "Ⅴ",
                "scale_type": "小(2)型水库",
                "main_building_level": 5,
                "flood_std_design": "20年一遇",
                "flood_std_check": "200年一遇",
                "catchment_area": 8.2,
                "total_investment": 890,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-HIS-004",
                "project_name": "自贡市富顺县琵琶镇土地滩水库除险加固工程",
                "project_type": ProjectType.RESERVOIR_REINFORCEMENT.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "自贡市富顺县水务局",
                "designer": "赵工",
                "department": "水工设计室",
                "location": "四川省自贡市富顺县",
                "river_basin": "长江流域-沱江水系",
                "project_grade": "Ⅳ",
                "scale_type": "小(1)型水库",
                "main_building_level": 4,
                "flood_std_design": "30年一遇",
                "flood_std_check": "500年一遇",
                "catchment_area": 15.6,
                "total_investment": 2100,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-HIS-005",
                "project_name": "成都市新都区泰兴排涝泵站新建工程",
                "project_type": ProjectType.DRAINAGE_PUMP.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "成都市新都区水务局",
                "designer": "刘工",
                "department": "市政给排水室",
                "location": "四川省成都市新都区",
                "river_basin": "长江流域-沱江水系",
                "project_grade": "Ⅳ",
                "scale_type": "中型泵站",
                "main_building_level": 4,
                "flood_std_design": "20年一遇",
                "catchment_area": 18.5,
                "total_investment": 4600,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-HIS-006",
                "project_name": "广元市昭化区山洪沟治理工程初步设计",
                "project_type": ProjectType.MOUNTAIN_FLOOD.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "广元市昭化区水务局",
                "designer": "杨工",
                "department": "河道设计室",
                "location": "四川省广元市昭化区",
                "river_basin": "长江流域-嘉陵江水系",
                "project_grade": "Ⅴ",
                "scale_type": "小(2)型",
                "main_building_level": 5,
                "flood_std_design": "10年一遇",
                "catchment_area": 22.8,
                "river_governance_length": 4.2,
                "total_investment": 1560,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-HIS-007",
                "project_name": "遂宁市安居区跑马滩灌区续建配套与节水改造工程",
                "project_type": ProjectType.IRRIGATION_UPGRADE.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "遂宁市安居区水利局",
                "designer": "黄工",
                "department": "灌溉设计室",
                "location": "四川省遂宁市安居区",
                "river_basin": "长江流域-涪江水系",
                "project_grade": "Ⅳ",
                "scale_type": "中型灌区",
                "main_building_level": 4,
                "irrigation_area": 5.2,
                "total_investment": 3800,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
            {
                "project_code": "PRJ-HIS-008",
                "project_name": "内江市市中区黄河镇水库饮用水源地保护工程",
                "project_type": ProjectType.RURAL_WATER.value,
                "design_stage": DesignStage.PRELIMINARY.value,
                "client": "内江市市中区水利局",
                "designer": "周工",
                "department": "水利室",
                "location": "四川省内江市市中区",
                "river_basin": "长江流域-沱江水系",
                "project_grade": "Ⅳ",
                "scale_type": "小(1)型",
                "main_building_level": 4,
                "total_investment": 2650,
                "status": ProjectStatus.ACTIVE.value,
                "created_by": "demo"
            },
        ]
        
        for p in sample_projects:
            project = DesignProject(**p)
            db.add(project)
        
        db.commit()
        print(f"示例项目初始化完成: {len(sample_projects)}个")
    else:
        print(f"项目数据已存在({project_count}个)，跳过示例项目初始化")
