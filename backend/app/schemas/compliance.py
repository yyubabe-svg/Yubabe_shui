"""
合规初审模块 Pydantic Schemas
用于API请求和响应的数据验证
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

class ProjectStatus(str, Enum):
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    REVIEWING = 'reviewing'
    RETURNED = 'returned'
    PASSED = 'passed'
    REJECTED = 'rejected'

class ReviewResult(str, Enum):
    PASS = 'pass'
    FAIL = 'fail'
    WARNING = 'warning'
    NA = 'na'

class PriorityLevel(str, Enum):
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'

class RiskLevel(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

class ReviewAction(str, Enum):
    SUBMIT = 'submit'
    ASSIGN = 'assign'
    REVIEW = 'review'
    RETURN = 'return'
    PASS = 'pass'
    REJECT = 'reject'

class CommentType(str, Enum):
    GENERAL = 'general'
    PROBLEM = 'problem'
    RECTIFICATION = 'rectification'
    REPLY = 'reply'

class CheckItemBase(BaseModel):
    category: Optional[str] = Field(None, description='检查类别')
    item_code: Optional[str] = Field(None, description='检查项编码')
    item_name: str = Field(..., description='检查项名称')
    item_description: Optional[str] = Field(None, description='检查项说明')
    check_standard: Optional[str] = Field(None, description='检查标准')
    check_method: Optional[str] = Field(None, description='检查方式')
    weight: float = Field(1.0, description='权重')
    score: float = Field(10.0, description='满分')
    is_required: bool = Field(True, description='是否必查')
    risk_level: str = Field('medium', description='风险等级')
    reference_docs: Optional[List[Dict[str, Any]]] = Field(None, description='参考文档')
    sort_order: int = Field(0, description='排序')

class CheckItemCreate(CheckItemBase):
    pass

class CheckItemUpdate(BaseModel):
    category: Optional[str] = None
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    item_description: Optional[str] = None
    check_standard: Optional[str] = None
    check_method: Optional[str] = None
    weight: Optional[float] = None
    score: Optional[float] = None
    is_required: Optional[bool] = None
    risk_level: Optional[str] = None
    reference_docs: Optional[List[Dict[str, Any]]] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class CheckItemResponse(CheckItemBase):
    id: int = Field(...)
    template_id: int = Field(...)
    is_active: bool = Field(...)
    created_at: datetime = Field(...)

    model_config = ConfigDict(from_attributes=True)

class ChecklistTemplateBase(BaseModel):
    template_code: str = Field(..., description='模板编码')
    template_name: str = Field(..., description='模板名称')
    template_type: Optional[str] = Field(None, description='适用项目类型')
    template_stage: Optional[str] = Field(None, description='适用项目阶段')
    description: Optional[str] = Field(None, description='模板说明')
    version: str = Field('1.0', description='版本号')

class ChecklistTemplateCreate(ChecklistTemplateBase):
    items: Optional[List[CheckItemCreate]] = Field(None, description='检查项列表')

class ChecklistTemplateUpdate(BaseModel):
    template_code: Optional[str] = None
    template_name: Optional[str] = None
    template_type: Optional[str] = None
    template_stage: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None

class ChecklistTemplateResponse(ChecklistTemplateBase):
    id: int = Field(...)
    is_active: bool = Field(...)
    created_by: Optional[int] = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    items: Optional[List[CheckItemResponse]] = None
    item_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class ComplianceProjectBase(BaseModel):
    project_code: str = Field(..., description='项目编号')
    project_name: str = Field(..., description='项目名称')
    project_type: Optional[str] = Field(None, description='项目类型')
    project_stage: Optional[str] = Field(None, description='项目阶段')
    applicant: Optional[str] = Field(None, description='申报单位/人')
    applicant_dept: Optional[str] = Field(None, description='申报部门')
    priority: str = Field('normal', description='优先级')
    pass_score: float = Field(60.0, description='及格分数线')
    deadline: Optional[datetime] = Field(None, description='审核截止时间')

class ComplianceProjectCreate(ComplianceProjectBase):
    template_id: Optional[int] = Field(None, description='使用的检查表模板ID')

class ComplianceProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    project_stage: Optional[str] = None
    applicant: Optional[str] = None
    applicant_dept: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    priority: Optional[str] = None
    pass_score: Optional[float] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None

class ComplianceProjectResponse(ComplianceProjectBase):
    id: int = Field(...)
    reviewer_id: Optional[int] = Field(...)
    reviewer_name: Optional[str] = Field(...)
    status: str = Field(...)
    total_score: float = Field(...)
    conclusion: Optional[str] = Field(...)
    summary: Optional[str] = Field(...)
    submitted_at: Optional[datetime] = Field(...)
    reviewed_at: Optional[datetime] = Field(...)
    created_by: Optional[int] = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    checklist_count: Optional[int] = None
    attachment_count: Optional[int] = None
    comment_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class ComplianceProjectListResponse(BaseModel):
    items: List[ComplianceProjectResponse] = Field(...)
    total: int = Field(...)
    page: int = Field(...)
    page_size: int = Field(...)
    statistics: Optional[Dict[str, Any]] = None

class ReviewItemBase(BaseModel):
    result: Optional[str] = Field(None, description='审核结果')
    score: float = Field(0.0, description='实际得分')
    issue_description: Optional[str] = Field(None, description='问题描述')
    rectification_suggestion: Optional[str] = Field(None, description='整改建议')
    evidence: Optional[List[Dict[str, Any]]] = Field(None, description='佐证材料')
    reviewer_note: Optional[str] = Field(None, description='审核人备注')

class ReviewItemUpdate(ReviewItemBase):
    pass

class ReviewItemResponse(ReviewItemBase):
    id: int = Field(...)
    checklist_id: int = Field(...)
    check_item_id: int = Field(...)
    category: Optional[str] = Field(...)
    item_name: str = Field(...)
    check_standard: Optional[str] = Field(...)
    weight: float = Field(...)
    full_score: float = Field(...)
    is_required: bool = Field(...)
    risk_level: str = Field(...)
    reviewed_by: Optional[int] = Field(...)
    reviewed_at: Optional[datetime] = Field(...)
    created_at: datetime = Field(...)

    model_config = ConfigDict(from_attributes=True)

class ChecklistInstanceResponse(BaseModel):
    id: int = Field(...)
    project_id: int = Field(...)
    template_id: int = Field(...)
    template_name: str = Field(...)
    total_items: int = Field(...)
    completed_items: int = Field(...)
    passed_items: int = Field(...)
    failed_items: int = Field(...)
    warning_items: int = Field(...)
    total_score: float = Field(...)
    created_at: datetime = Field(...)
    review_items: Optional[List[ReviewItemResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class ComplianceReviewCreate(BaseModel):
    action: str = Field(..., description='操作类型')
    opinion: Optional[str] = Field(None, description='审核意见')
    reviewer_id: Optional[int] = Field(None, description='指派的审核人ID')
    reviewer_name: Optional[str] = Field(None, description='指派的审核人姓名')
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description='附件')
    review_items: Optional[List[ReviewItemUpdate]] = Field(None, description='审核项结果')
    conclusion: Optional[str] = Field(None, description='审核结论')
    summary: Optional[str] = Field(None, description='审核总结')

class ComplianceReviewResponse(BaseModel):
    id: int = Field(...)
    project_id: int = Field(...)
    review_round: int = Field(...)
    action: str = Field(...)
    operator_id: Optional[int] = Field(...)
    operator_name: Optional[str] = Field(...)
    operator_dept: Optional[str] = Field(...)
    opinion: Optional[str] = Field(...)
    result_data: Optional[Dict[str, Any]] = Field(...)
    attachments: Optional[List[Dict[str, Any]]] = Field(...)
    created_at: datetime = Field(...)

    model_config = ConfigDict(from_attributes=True)

class CommentBase(BaseModel):
    content: str = Field(..., description='评论内容')
    comment_type: str = Field('general', description='评论类型')
    is_private: bool = Field(False, description='是否仅内部可见')
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description='附件列表')

class CommentCreate(CommentBase):
    parent_id: Optional[int] = Field(None, description='回复的父评论ID')

class CommentUpdate(BaseModel):
    content: Optional[str] = None
    comment_type: Optional[str] = None
    is_private: Optional[bool] = None

class CommentResponse(CommentBase):
    id: int = Field(...)
    project_id: int = Field(...)
    parent_id: Optional[int] = Field(...)
    author_id: Optional[int] = Field(...)
    author_name: Optional[str] = Field(...)
    author_dept: Optional[str] = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    replies: Optional[List['CommentResponse']] = None

    model_config = ConfigDict(from_attributes=True)

class AttachmentResponse(BaseModel):
    id: int = Field(...)
    project_id: int = Field(...)
    file_name: str = Field(...)
    file_path: str = Field(...)
    file_type: Optional[str] = Field(...)
    file_size: Optional[int] = Field(...)
    mime_type: Optional[str] = Field(...)
    category: Optional[str] = Field(...)
    uploader_id: Optional[int] = Field(...)
    uploader_name: Optional[str] = Field(...)
    description: Optional[str] = Field(...)
    is_required: bool = Field(...)
    created_at: datetime = Field(...)

    model_config = ConfigDict(from_attributes=True)

class ComplianceStatistics(BaseModel):
    total_projects: int = Field(0, description='总项目数')
    draft_count: int = Field(0, description='草稿数')
    pending_count: int = Field(0, description='待审核数')
    reviewing_count: int = Field(0, description='审核中数')
    returned_count: int = Field(0, description='退回数')
    passed_count: int = Field(0, description='通过数')
    rejected_count: int = Field(0, description='不通过数')
    avg_score: float = Field(0.0, description='平均得分')
    avg_review_days: float = Field(0.0, description='平均审核天数')
    pass_rate: float = Field(0.0, description='通过率')
    by_type: Dict[str, int] = Field(default_factory=dict, description='按类型统计')
    by_month: List[Dict[str, Any]] = Field(default_factory=list, description='按月份统计')

class ComplianceProjectDetail(ComplianceProjectResponse):
    checklists: Optional[List[ChecklistInstanceResponse]] = None
    reviews: Optional[List[ComplianceReviewResponse]] = None
    comments: Optional[List[CommentResponse]] = None
    attachments: Optional[List[AttachmentResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class BatchAssignRequest(BaseModel):
    project_ids: List[int] = Field(...)
    reviewer_id: int = Field(...)
    reviewer_name: str = Field(...)

class BatchSubmitRequest(BaseModel):
    project_ids: List[int] = Field(...)

CommentResponse.model_rebuild()
