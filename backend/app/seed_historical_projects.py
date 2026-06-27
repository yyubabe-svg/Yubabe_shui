"""
补充历史项目种子数据 - 为历史复用推荐增加样例数据
运行: python -m app.seed_historical_projects
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.project import DesignProject, ProjectType, DesignStage, ProjectStatus

historical_projects = [
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


def seed():
    db = SessionLocal()
    try:
        added = 0
        for p_data in historical_projects:
            existing = db.query(DesignProject).filter(
                DesignProject.project_code == p_data["project_code"]
            ).first()
            if existing:
                continue
            project = DesignProject(**p_data)
            db.add(project)
            added += 1
        db.commit()
        print(f"成功补充 {added} 个历史项目")
    except Exception as e:
        db.rollback()
        print(f"补充历史项目失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
