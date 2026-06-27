"""
AI 初审模块 Pydantic Schemas
对应模型：AIReviewTask / AIReviewIssue
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============ 枚举值（与 models/ai_review.py 对齐） ============

REVIEW_DIMENSIONS = [
    "param_completeness",      # 参数完整性
    "code_compliance",         # 规范符合性
    "chapter_completeness",    # 章节完整性
    "value_consistency",       # 数值一致性
    "format_standard",         # 格式规范性
]

ISSUE_SEVERITY_MAP = {
    "critical": "严重（强条违反）",
    "major": "重要",
    "minor": "一般",
    "suggestion": "建议优化",
}

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "suggestion": 3}


# ============ 请求体 ============

class ReviewTaskCreate(BaseModel):
    """创建 AI 审查任务"""
    project_id: int
    document_id: int
    dimensions: List[str] = Field(
        default_factory=lambda: list(REVIEW_DIMENSIONS),
        description="审查维度列表，默认全选"
    )
    project_type_hint: Optional[str] = Field(None, description="项目类型提示")
    design_stage_hint: Optional[str] = Field(None, description="设计阶段提示")
    created_by: Optional[str] = None


class ReviewIssueUpdate(BaseModel):
    """更新审查问题状态/备注"""
    status: Optional[str] = Field(None, description="open/accepted/rejected/fixed")
    note: Optional[str] = None


class ReviewReRunRequest(BaseModel):
    """重新审查（可选指定维度）"""
    dimensions: Optional[List[str]] = None


# ============ 内部 DTO（LLM 结构化输出） ============

class ChapterIssueItem(BaseModel):
    """单条问题（LLM JSON 输出结构）"""
    severity: str = Field(..., description="critical/major/minor/suggestion")
    category: str = Field(..., description="审查维度")
    chapter_path: Optional[str] = Field(None, description="章节路径，如 '3.2 堤顶高程'")
    page_number: Optional[int] = None
    location_desc: Optional[str] = Field(None, description="位置描述")
    description: str = Field(..., description="问题描述")
    basis_code: Optional[str] = Field(None, description="规范依据")
    suggestion: Optional[str] = Field(None, description="修改建议")
    original_text: Optional[str] = Field(None, description="原文摘录")


class ChapterReviewResult(BaseModel):
    """单章节审查结果"""
    chapter_path: str
    issues: List[ChapterIssueItem] = Field(default_factory=list)
    chapter_score: Optional[float] = None
    chapter_summary: Optional[str] = None


# ============ 响应体 ============

class ReviewIssueOut(BaseModel):
    """审查问题响应"""
    id: int
    review_task_id: int
    severity: str
    category: str
    chapter_path: Optional[str]
    page_number: Optional[int]
    location_desc: Optional[str]
    description: str
    basis_code: Optional[str]
    suggestion: Optional[str]
    original_text: Optional[str]
    status: str
    note: Optional[str]
    severity_label: Optional[str] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ReviewTaskOut(BaseModel):
    """审查任务响应"""
    id: int
    project_id: int
    document_id: int
    status: str
    review_dimensions: Optional[List[str]] = None
    project_type_hint: Optional[str]
    design_stage_hint: Optional[str]
    total_score: Optional[float]
    summary: Optional[str]
    issue_count_critical: int
    issue_count_major: int
    issue_count_minor: int
    issue_count_suggestion: int
    total_issues: int
    duration_seconds: Optional[int]
    progress: int
    current_chapter: Optional[str]
    error_message: Optional[str]
    created_by: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ReviewTaskDetailOut(ReviewTaskOut):
    """审查任务详情（含问题列表）"""
    issues: List[ReviewIssueOut] = Field(default_factory=list)


class ReviewProgressEvent(BaseModel):
    """SSE 进度事件"""
    event: str = Field(..., description="progress/chapter_complete/done/error")
    task_id: int
    progress: Optional[int] = None
    current_chapter: Optional[str] = None
    chapter_result: Optional[ChapterReviewResult] = None
    message: Optional[str] = None
    error: Optional[str] = None


class ReviewExportOut(BaseModel):
    """导出结果"""
    task_id: int
    file_path: str
    file_name: str
    issue_count: int
    exported_at: datetime
