"""
合规初审模块 Pydantic Schemas
用于API请求和响应的数据验证
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============ 枚举定义 ============

class ProjectStatus(str, Enum):
    """项目状态枚举"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    RETURNED = "returned"
    PASSED = "passed"
    REJECTED = "rejected"


class ReviewResult(str, Enum):
    """审核结果枚举"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NA = "na"


class PriorityLevel(str, Enum):
    """优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewAction(str, Enum):
    """审核操作枚举"""
    SUBMIT = "submit"
    ASSIGN = "assign"
    REVIEW = "review"
    RETURN = "return"
    PASS = "pass"
    REJECT = "reject"


class CommentType(str, Enum):
    """评论类型枚举"""
    GENERAL = "general"
    PROBLEM = "problem"
    RECTIFICATION = "rectification"
    REPLY = "reply"


# ============ 检查项模板相关 ============

class CheckItemBase(BaseModel):
    category: Optional[str] = Field(None, description="检查类别")
    item_code: Optional[str] = Field(None, description="检查项编码")
    item_name: str = Field(..., description="检查项名称")
    item_description: Optional[str] = Field(None, description="检查项说明")
    check_standard: Optional[str] = Field(None, description="检查标准")
    check_method: Optional[str] = Field(None, description="检查方式")
    weight: float = Field(1.0, description="权重")
    score: float = Field(10.0, description="满分")
    is_required: bool = Field(True, description="是否必查")
    risk_level: str = Field("medium", description="风险等级")
    reference_docs: Optional[List[Dict[str, Any]]] = Field(None, description="参考文档")
    sort_order: int = Field(0, description="排序")


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
    id: int
    template_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChecklistTemplateBase(BaseModel):
    template_code: str = Field(..., description="模板编码")
    template_name: str = Field(..., description="模板名称")
    template_type: Optional[str] = Field(None, description="适用项目类型")
    template_stage: Optional[str] = Field(None, description="适用项目阶段")
    description: Optional[str] = Field(None, description="模板说明")
    version: str = Field("1.0", description="版本号")


class ChecklistTemplateCreate(ChecklistTemplateBase):
    items: Optional[List[CheckItemCreate]] = Field(None, description="检查项列表")


class ChecklistTemplateUpdate(BaseModel):
    template_code: Optional[str] = None
    template_name: Optional[str] = None
    template_type: Optional[str] = None
    template_stage: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None


class ChecklistTemplateResponse(ChecklistTemplateBase):
    id: int
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    items: Optional[List[CheckItemResponse]] = None
    item_count: Optional[int] = None

    class Config:
        from_attributes = True


# ============ 初审项目相关 ============

class ComplianceProjectBase(BaseModel):
    project_code: str = Field(..., description="项目编号")
    project_name: str = Field(..., description="项目名称")
    project_type: Optional[str] = Field(None, description="项目类型")
    project_stage: Optional[str] = Field(None, description="项目阶段")
    applicant: Optional[str] = Field(None, description="申报单位/人")
    applicant_dept: Optional[str] = Field(None, description="申报部门")
    priority: str = Field("normal", description="优先级")
    pass_score: float = Field(60.0, description="及格分数线")
    deadline: Optional[datetime] = Field(None, description="审核截止时间")


class ComplianceProjectCreate(ComplianceProjectBase):
    template_id: Optional[int] = Field(None, description="使用的检查表模板ID")


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
    id: int
    reviewer_id: Optional[int]
    reviewer_name: Optional[str]
    status: str
    total_score: float
    conclusion: Optional[str]
    summary: Optional[str]
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    checklist_count: Optional[int] = None
    attachment_count: Optional[int] = None
    comment_count: Optional[int] = None

    class Config:
        from_attributes = True


class ComplianceProjectListResponse(BaseModel):
    """项目列表响应（含统计信息）"""
    items: List[ComplianceProjectResponse]
    total: int
    page: int
    page_size: int
    statistics: Optional[Dict[str, Any]] = None


# ============ 检查表实例相关 ============

class ReviewItemBase(BaseModel):
    result: Optional[str] = Field(None, description="审核结果")
    score: float = Field(0.0, description="实际得分")
    issue_description: Optional[str] = Field(None, description="问题描述")
    rectification_suggestion: Optional[str] = Field(None, description="整改建议")
    evidence: Optional[List[Dict[str, Any]]] = Field(None, description="佐证材料")
    reviewer_note: Optional[str] = Field(None, description="审核人备注")


class ReviewItemUpdate(ReviewItemBase):
    pass


class ReviewItemResponse(ReviewItemBase):
    id: int
    checklist_id: int
    check_item_id: int
    category: Optional[str]
    item_name: str
    check_standard: Optional[str]
    weight: float
    full_score: float
    is_required: bool
    risk_level: str
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ChecklistInstanceResponse(BaseModel):
    id: int
    project_id: int
    template_id: int
    template_name: str
    total_items: int
    completed_items: int
    passed_items: int
    failed_items: int
    warning_items: int
    total_score: float
    created_at: datetime
    review_items: Optional[List[ReviewItemResponse]] = None

    class Config:
        from_attributes = True


# ============ 审核流程相关 ============

class ComplianceReviewCreate(BaseModel):
    action: str = Field(..., description="操作类型")
    opinion: Optional[str] = Field(None, description="审核意见")
    reviewer_id: Optional[int] = Field(None, description="指派的审核人ID")
    reviewer_name: Optional[str] = Field(None, description="指派的审核人姓名")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件")
    review_items: Optional[List[ReviewItemUpdate]] = Field(None, description="审核项结果")
    conclusion: Optional[str] = Field(None, description="审核结论")
    summary: Optional[str] = Field(None, description="审核总结")


class ComplianceReviewResponse(BaseModel):
    id: int
    project_id: int
    review_round: int
    action: str
    operator_id: Optional[int]
    operator_name: Optional[str]
    operator_dept: Optional[str]
    opinion: Optional[str]
    result_data: Optional[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 评论相关 ============

class CommentBase(BaseModel):
    content: str = Field(..., description="评论内容")
    comment_type: str = Field("general", description="评论类型")
    is_private: bool = Field(False, description="是否仅内部可见")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")


class CommentCreate(CommentBase):
    parent_id: Optional[int] = Field(None, description="回复的父评论ID")


class CommentUpdate(BaseModel):
    content: Optional[str] = None
    comment_type: Optional[str] = None
    is_private: Optional[bool] = None


class CommentResponse(CommentBase):
    id: int
    project_id: int
    parent_id: Optional[int]
    author_id: Optional[int]
    author_name: Optional[str]
    author_dept: Optional[str]
    created_at: datetime
    updated_at: datetime
    replies: Optional[List["CommentResponse"]] = None

    class Config:
        from_attributes = True


# ============ 附件相关 ============

class AttachmentResponse(BaseModel):
    id: int
    project_id: int
    file_name: str
    file_path: str
    file_type: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    category: Optional[str]
    uploader_id: Optional[int]
    uploader_name: Optional[str]
    description: Optional[str]
    is_required: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 统计相关 ============

class ComplianceStatistics(BaseModel):
    """合规初审统计数据"""
    total_projects: int = Field(0, description="总项目数")
    draft_count: int = Field(0, description="草稿数")
    pending_count: int = Field(0, description="待审核数")
    reviewing_count: int = Field(0, description="审核中数")
    returned_count: int = Field(0, description="退回数")
    passed_count: int = Field(0, description="通过数")
    rejected_count: int = Field(0, description="不通过数")
    avg_score: float = Field(0.0, description="平均得分")
    avg_review_days: float = Field(0.0, description="平均审核天数")
    pass_rate: float = Field(0.0, description="通过率")
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    by_month: List[Dict[str, Any]] = Field(default_factory=list, description="按月份统计")


class ComplianceProjectDetail(ComplianceProjectResponse):
    """项目详情（含关联数据）"""
    checklists: Optional[List[ChecklistInstanceResponse]] = None
    reviews: Optional[List[ComplianceReviewResponse]] = None
    comments: Optional[List[CommentResponse]] = None
    attachments: Optional[List[AttachmentResponse]] = None


# ============ 批量操作 ============

class BatchAssignRequest(BaseModel):
    """批量分配请求"""
    project_ids: List[int]
    reviewer_id: int
    reviewer_name: str


class BatchSubmitRequest(BaseModel):
    """批量提交请求"""
    project_ids: List[int]


# 解决循环引用
CommentResponse.model_rebuild()
