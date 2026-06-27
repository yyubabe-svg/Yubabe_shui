"""
专家意见回复模块 Pydantic Schemas
对应模型：ExpertReplyTask / ExpertOpinion / ExpertReplyItem
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ 枚举值映射 ============

MODIFY_STATUS_OPTIONS = ["已修改", "已补充", "解释说明", "不修改"]

OPINION_TYPE_MAP = {
    "modify": "修改类",
    "supplement": "补充类",
    "explain": "解释说明类",
    "other": "其他",
}

MAJOR_CATEGORY_MAP = {
    "hydrology": "水文",
    "geology": "地质",
    "hydraulic": "水工",
    "construction": "施工",
    "investment": "投资概算",
    "soil_conservation": "水土保持",
    "environment": "环境",
    "electromechanical": "机电金结",
    "resettlement": "移民占地",
    "format": "格式文字",
    "other": "其他",
}


# ============ 请求体 ============

class ReplyTaskCreate(BaseModel):
    """创建专家意见回复任务"""
    project_id: int
    opinion_doc_id: int = Field(..., description="意见文档ID")
    report_doc_id: Optional[int] = Field(None, description="关联报告文档ID")
    meeting_name: Optional[str] = None
    meeting_date: Optional[str] = None
    created_by: Optional[str] = None


class ReplyGenerateRequest(BaseModel):
    """生成单条意见回复"""
    opinion_id: int
    force_regenerate: bool = Field(False, description="是否强制重新生成")


class ReplyUpdateRequest(BaseModel):
    """更新回复内容"""
    reply_content: Optional[str] = None
    modify_status: Optional[str] = Field(None, description="已修改/已补充/解释说明/不修改")
    modify_location: Optional[str] = None
    modify_page: Optional[str] = None
    status: Optional[str] = Field(None, description="draft/confirmed")


class ReplyBatchGenerateRequest(BaseModel):
    """批量生成回复"""
    opinion_ids: Optional[List[int]] = Field(None, description="指定意见ID列表，None 表示全部未生成")


# ============ 内部 DTO（LLM 结构化输出） ============

class ParsedOpinionItem(BaseModel):
    """解析出的单条意见"""
    opinion_index: int
    expert_name: Optional[str] = None
    major_category: Optional[str] = Field(None, description="专业分类 key")
    opinion_type: str = Field(..., description="modify/supplement/explain/other")
    content: str
    page_number: Optional[int] = None
    chapter_path: Optional[str] = None


class ReplyGenerateResult(BaseModel):
    """回复生成结果"""
    reply_content: str
    modify_status: str = Field(..., description="已修改/已补充/解释说明/不修改")
    modify_location: Optional[str] = None
    modify_page: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


# ============ 响应体 ============

class ReplyItemOut(BaseModel):
    """回复项响应"""
    id: int
    opinion_id: int
    reply_content: str
    modify_status: str
    modify_location: Optional[str]
    modify_page: Optional[str]
    status: str
    sources_json: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OpinionOut(BaseModel):
    """专家意见响应"""
    id: int
    reply_task_id: int
    opinion_index: Optional[int]
    order_index: int
    expert_name: Optional[str]
    major_category: Optional[str]
    major_category_name: Optional[str] = None
    opinion_type: Optional[str]
    opinion_type_name: Optional[str] = None
    content: str
    page_number: Optional[int]
    chapter_path: Optional[str]
    created_at: Optional[datetime]
    reply_item: Optional[ReplyItemOut] = None

    model_config = {"from_attributes": True}


class ReplyTaskOut(BaseModel):
    """回复任务响应"""
    id: int
    project_id: int
    opinion_document_id: int
    report_document_id: Optional[int]
    status: str
    meeting_name: Optional[str]
    meeting_date: Optional[str]
    expert_count: int
    opinion_count: int
    output_file_path: Optional[str]
    output_filename: Optional[str]
    error_message: Optional[str]
    progress: int
    created_by: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ReplyTaskDetailOut(ReplyTaskOut):
    """回复任务详情（含意见列表）"""
    opinions: List[OpinionOut] = Field(default_factory=list)


class ReplyProgressEvent(BaseModel):
    """SSE 进度事件"""
    event: str = Field(..., description="progress/opinion_parsed/reply_generated/done/error")
    task_id: int
    progress: Optional[int] = None
    opinion_index: Optional[int] = None
    current_opinion: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class ReplyExportOut(BaseModel):
    """导出结果"""
    task_id: int
    file_path: str
    file_name: str
    opinion_count: int
    replied_count: int
    exported_at: datetime
