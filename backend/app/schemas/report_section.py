"""
报告章节生成模块 Pydantic Schemas
对应模型：ReportSectionTemplate / ReportSectionTask / ReportSectionDraft
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ 请求体 ============

class SectionTaskCreate(BaseModel):
    """创建章节生成任务"""
    project_id: int
    template_id: int
    doc_ids: Optional[List[int]] = Field(default_factory=list, description="参考文档ID列表")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="用户补充/覆盖的参数")
    created_by: Optional[str] = None


class OutlineUpdate(BaseModel):
    """编辑大纲"""
    outline_json: Dict[str, Any] = Field(..., description="更新后的大纲JSON")


class ParagraphAccept(BaseModel):
    """接受段落"""
    paragraph_id: str


class ParagraphEdit(BaseModel):
    """编辑段落内容"""
    paragraph_id: str
    content: str
    note: Optional[str] = None


class ParagraphRegenerate(BaseModel):
    """重新生成段落"""
    paragraph_id: str
    feedback: Optional[str] = Field(None, description="重写反馈/要求")


class SectionStreamRequest(BaseModel):
    """SSE 流式生成请求"""
    task_id: int
    start_from_paragraph: Optional[str] = Field(None, description="从指定段落开始生成（断点续传）")


# ============ 内部 DTO（LLM 结构化输出） ============

class OutlineItem(BaseModel):
    """大纲条目"""
    paragraph_id: str = Field(..., description="段落ID，如 heading_1, para_3")
    parent_paragraph_id: Optional[str] = None
    paragraph_type: str = Field(..., description="heading/paragraph/list/table")
    level: Optional[int] = Field(None, description="标题层级")
    title: str = Field(..., description="标题/段落概要")
    writing_instruction: Optional[str] = Field(None, description="写作要点")
    keywords: Optional[List[str]] = Field(default_factory=list, description="检索关键词")


class OutlineResult(BaseModel):
    """大纲生成结果"""
    chapter_title: str
    chapter_number: str
    items: List[OutlineItem] = Field(default_factory=list)


class GeneratedParagraph(BaseModel):
    """生成的单段落结果"""
    paragraph_id: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


# ============ 响应体 ============

class SectionTemplateOut(BaseModel):
    """章节模板响应"""
    id: int
    chapter_number: str
    title: str
    parent_id: Optional[int]
    level: int
    applicable_project_types: Optional[List[str]] = None
    applicable_stages: Optional[List[str]] = None
    required_params: Optional[List[str]] = None
    description: Optional[str]
    sort_order: int

    model_config = {"from_attributes": True}


class DraftParagraphOut(BaseModel):
    """草稿段落响应"""
    id: int
    task_id: int
    paragraph_id: str
    parent_paragraph_id: Optional[str]
    paragraph_type: str
    level: Optional[int]
    content: str
    status: str
    sources_json: Optional[List[Dict[str, Any]]] = None
    sort_order: int
    feedback: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SectionTaskOut(BaseModel):
    """章节生成任务响应"""
    id: int
    project_id: int
    template_id: int
    document_ids: Optional[List[int]] = None
    status: str
    params_override: Optional[Dict[str, Any]] = None
    outline_json: Optional[Dict[str, Any]] = None
    assembled_content: Optional[str]
    output_file_path: Optional[str]
    output_filename: Optional[str]
    error_message: Optional[str]
    progress: int
    created_by: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SectionTaskDetailOut(SectionTaskOut):
    """章节任务详情（含段落列表）"""
    drafts: List[DraftParagraphOut] = Field(default_factory=list)
    template: Optional[SectionTemplateOut] = None


class SectionStreamEvent(BaseModel):
    """SSE 流式生成事件"""
    event: str = Field(..., description="outline/paragraph_start/paragraph_delta/paragraph_done/done/error")
    task_id: int
    paragraph_id: Optional[str] = None
    paragraph_type: Optional[str] = None
    delta: Optional[str] = None
    content: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class SectionExportOut(BaseModel):
    """导出结果"""
    task_id: int
    file_path: str
    file_name: str
    paragraph_count: int
    exported_at: datetime
