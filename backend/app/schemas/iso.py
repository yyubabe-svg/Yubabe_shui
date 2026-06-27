from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ISOProjectInfo(BaseModel):
    project_name: str
    project_code: str
    feature_code: str
    design_stage: str
    report_date: Optional[str] = None
    client: Optional[str] = None
    department: str = "水利设计院"
    work_scope: Optional[str] = None
    engineering_overview: Optional[str] = None
    design_basis: Optional[str] = None
    technical_points: Optional[str] = None
    risk_points: Optional[str] = None
    customer_requirements: Optional[str] = None
    external_resources: Optional[str] = None
    quality_level: str
    project_grade: Optional[str] = None
    building_level: Optional[str] = None
    flood_standard: Optional[str] = None
    drainage_standard: Optional[str] = None
    involved_majors: List[str] = []
    excluded_majors: List[str] = []
    applicable_codes: List[Dict[str, str]] = []
    design_review_method: str = "会议评审"
    design_verification_method: str = "产品校审"
    design_confirmation_method: str = "项目审查"


class ISOGenerateRequest(BaseModel):
    document_id: Optional[int] = None
    file_path: Optional[str] = None
    project_manager: Optional[str] = None
    supplementary_info: Optional[Dict[str, Any]] = {}


class ISOGenerateResponse(BaseModel):
    task_id: str
    status: str
    project_info: Optional[ISOProjectInfo] = None
    output_file: Optional[str] = None
    download_url: Optional[str] = None
    message: Optional[str] = None
    warnings: List[str] = []


class ISOFillRequest(BaseModel):
    task_id: str
    project_info: ISOProjectInfo
    staff_config: Optional[Dict[str, Any]] = {}


class ISOHistoryItem(BaseModel):
    id: int
    project_name: str
    project_code: str
    design_stage: str
    created_at: str
    file_name: str
    status: str
