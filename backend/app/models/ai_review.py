import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReviewStatus(str, enum.Enum):
    """审查任务状态"""
    PENDING = "pending"           # 待审查
    REVIEWING = "reviewing"       # 审查中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败


class IssueSeverity(str, enum.Enum):
    """问题严重程度"""
    CRITICAL = "critical"         # 严重（强条违反）
    MAJOR = "major"               # 重要
    MINOR = "minor"               # 一般
    SUGGESTION = "suggestion"     # 建议优化


class IssueCategory(str, enum.Enum):
    """问题分类"""
    PARAM_COMPLETENESS = "param_completeness"    # 参数完整性
    CODE_COMPLIANCE = "code_compliance"          # 规范符合性
    CHAPTER_COMPLETENESS = "chapter_completeness"  # 章节完整性
    VALUE_CONSISTENCY = "value_consistency"      # 数值一致性
    FORMAT_STANDARD = "format_standard"          # 格式规范性


class IssueStatus(str, enum.Enum):
    """问题处理状态"""
    OPEN = "open"                 # 待处理
    ACCEPTED = "accepted"         # 已接受
    REJECTED = "rejected"         # 已拒绝
    FIXED = "fixed"               # 已修复


class AIReviewTask(Base):
    """AI初审任务"""
    __tablename__ = "ai_review_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("design_projects.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    status = Column(String(30), default=ReviewStatus.PENDING.value, index=True)
    review_dimensions = Column(JSON)  # 勾选的审查维度列表
    project_type_hint = Column(String(50))  # 项目类型提示
    design_stage_hint = Column(String(30))  # 设计阶段提示
    total_score = Column(Float)  # 总分0-100
    summary = Column(Text)  # 审查总结
    issue_count_critical = Column(Integer, default=0)
    issue_count_major = Column(Integer, default=0)
    issue_count_minor = Column(Integer, default=0)
    issue_count_suggestion = Column(Integer, default=0)
    duration_seconds = Column(Integer)  # 审查耗时
    error_message = Column(Text)
    progress = Column(Integer, default=0)
    current_chapter = Column(String(200))  # 当前审查章节
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # 关系
    project = relationship("DesignProject", back_populates="review_tasks")
    document = relationship("Document")
    issues = relationship("AIReviewIssue", back_populates="review_task", cascade="all, delete-orphan", order_by="AIReviewIssue.severity_order, AIReviewIssue.id")

    @property
    def status_enum(self):
        try:
            return ReviewStatus(self.status)
        except (ValueError, TypeError):
            return ReviewStatus.PENDING

    @property
    def total_issues(self):
        return (self.issue_count_critical or 0) + (self.issue_count_major or 0) + \
               (self.issue_count_minor or 0) + (self.issue_count_suggestion or 0)


class AIReviewIssue(Base):
    """AI初审问题"""
    __tablename__ = "ai_review_issues"

    id = Column(Integer, primary_key=True, index=True)
    review_task_id = Column(Integer, ForeignKey("ai_review_tasks.id"), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    category = Column(String(30), nullable=False, index=True)
    chapter_path = Column(String(200))  # 章节路径 如 "3.2 堤顶高程"
    page_number = Column(Integer)  # 页码
    location_desc = Column(String(500))  # 位置描述
    description = Column(Text, nullable=False)  # 问题描述
    basis_code = Column(String(500))  # 规范依据
    suggestion = Column(Text)  # 修改建议
    original_text = Column(Text)  # 原文摘录
    status = Column(String(20), default=IssueStatus.OPEN.value)
    note = Column(Text)  # 人工备注
    severity_order = Column(Integer, default=0)  # 排序用：critical=0, major=1, minor=2, suggestion=3
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    review_task = relationship("AIReviewTask", back_populates="issues")

    @property
    def severity_enum(self):
        try:
            return IssueSeverity(self.severity)
        except (ValueError, TypeError):
            return IssueSeverity.MINOR

    @property
    def category_enum(self):
        try:
            return IssueCategory(self.category)
        except (ValueError, TypeError):
            return IssueCategory.FORMAT_STANDARD

    @property
    def status_enum(self):
        try:
            return IssueStatus(self.status)
        except (ValueError, TypeError):
            return IssueStatus.OPEN
