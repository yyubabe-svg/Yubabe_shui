import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class SectionTaskStatus(str, enum.Enum):
    """章节生成任务状态"""
    PENDING = "pending"           # 待处理
    OUTLINE_GENERATING = "outline_generating"  # 大纲生成中
    GENERATING = "generating"     # 生成中
    EDITING = "editing"           # 编辑中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败


class DraftStatus(str, enum.Enum):
    """草稿段落状态"""
    PENDING = "pending"           # 待生成
    GENERATED = "generated"       # 已生成
    ACCEPTED = "accepted"         # 已接受
    EDITED = "edited"             # 已编辑
    REGENERATED = "regenerated"   # 已重写


class ParagraphType(str, enum.Enum):
    """段落类型"""
    HEADING = "heading"           # 标题
    PARAGRAPH = "paragraph"       # 段落
    LIST = "list"                 # 列表
    TABLE = "table"               # 表格


class ReportSectionTemplate(Base):
    """报告章节模板"""
    __tablename__ = "report_section_templates"

    id = Column(Integer, primary_key=True, index=True)
    chapter_number = Column(String(20), nullable=False, index=True)  # 章节编号 如 "1", "3.2"
    title = Column(String(200), nullable=False)
    parent_id = Column(Integer, ForeignKey("report_section_templates.id"))
    level = Column(Integer, default=1)  # 层级1/2/3
    applicable_project_types = Column(JSON)  # 适用项目类型
    applicable_stages = Column(JSON)  # 适用设计阶段
    writing_prompt = Column(Text)  # 写作指导prompt
    required_params = Column(JSON)  # 必需参数列表
    reference_keywords = Column(JSON)  # 参考检索关键词
    sub_sections_outline = Column(JSON)  # 默认子节大纲
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    parent = relationship("ReportSectionTemplate", remote_side=[id], backref="children")
    tasks = relationship("ReportSectionTask", back_populates="template")


class ReportSectionTask(Base):
    """章节生成任务"""
    __tablename__ = "report_section_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("design_projects.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("report_section_templates.id"), nullable=False)
    document_ids = Column(JSON)  # 参考文档ID列表
    status = Column(String(30), default=SectionTaskStatus.PENDING.value, index=True)
    params_override = Column(JSON)  # 用户补充/覆盖的参数
    outline_json = Column(JSON)  # 详细大纲（LLM生成后可编辑）
    assembled_content = Column(Text)  # 汇总后的完整内容
    output_file_path = Column(String(500))
    output_filename = Column(String(255))
    error_message = Column(Text)
    progress = Column(Integer, default=0)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # 关系
    project = relationship("DesignProject", back_populates="section_tasks")
    template = relationship("ReportSectionTemplate", back_populates="tasks")
    drafts = relationship("ReportSectionDraft", back_populates="task", cascade="all, delete-orphan", order_by="ReportSectionDraft.sort_order")

    @property
    def status_enum(self):
        try:
            return SectionTaskStatus(self.status)
        except (ValueError, TypeError):
            return SectionTaskStatus.PENDING


class ReportSectionDraft(Base):
    """章节草稿段落"""
    __tablename__ = "report_section_drafts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("report_section_tasks.id"), nullable=False, index=True)
    paragraph_id = Column(String(50))  # 段落标识（如 "heading_1", "para_3"）
    parent_paragraph_id = Column(String(50))  # 父段落ID
    paragraph_type = Column(String(20), default=ParagraphType.PARAGRAPH.value)
    level = Column(Integer)  # 标题层级（heading类型时使用）
    content = Column(Text, nullable=False)
    status = Column(String(30), default=DraftStatus.PENDING.value)
    sources_json = Column(JSON)  # 来源引用 [{document_id, page, section}]
    sort_order = Column(Integer, default=0)
    feedback = Column(Text)  # 用户反馈（重写时使用）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    task = relationship("ReportSectionTask", back_populates="drafts")

    @property
    def status_enum(self):
        try:
            return DraftStatus(self.status)
        except (ValueError, TypeError):
            return DraftStatus.PENDING
