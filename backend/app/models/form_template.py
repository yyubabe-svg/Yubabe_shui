import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class FormTemplateType(str, enum.Enum):
    """表单模板类型"""
    ISO = "iso"                           # ISO管理体系表格
    APPROVAL = "approval"                 # 审批/校审表格
    REVIEW_REPLY = "review_reply"         # 评审意见回复表
    PROJECT_FEATURE = "project_feature"   # 工程特性表
    QUALITY = "quality"                   # 质量认证表
    OTHER = "other"                       # 其他


class FormFillStatus(str, enum.Enum):
    """填报任务状态"""
    PENDING = "pending"                   # 待处理
    EXTRACTING = "extracting"             # 提取中
    FILLING = "filling"                   # 填充中
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # 待确认
    COMPLETED = "completed"               # 已完成
    FAILED = "failed"                     # 失败


class FormFieldType(str, enum.Enum):
    """字段类型"""
    TEXT = "text"                         # 单行文本
    TEXTAREA = "textarea"                 # 多行文本
    SELECT = "select"                     # 下拉选择
    CHECKBOX = "checkbox"                 # 复选框
    DATE = "date"                         # 日期
    NUMBER = "number"                     # 数字


class LocatorType(str, enum.Enum):
    """单元格定位方式"""
    TABLE_CELL = "table_cell"             # 表格行列定位
    BOOKMARK = "bookmark"                 # Word书签定位
    LABEL_ADJACENT = "label_adjacent"     # 标签相邻定位


class FormTemplate(Base):
    """表单模板"""
    __tablename__ = "form_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_code = Column(String(50), unique=True, index=True, nullable=False)
    template_name = Column(String(200), nullable=False)
    template_file_path = Column(String(500))  # 模板文件路径
    template_type = Column(String(30), default=FormTemplateType.OTHER.value)
    applicable_project_types = Column(JSON)   # 适用项目类型列表
    description = Column(Text)
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    fields = relationship("FormField", back_populates="template", cascade="all, delete-orphan")
    fill_tasks = relationship("FormFillTask", back_populates="template", cascade="all, delete-orphan")

    @property
    def template_type_enum(self):
        try:
            return FormTemplateType(self.template_type)
        except (ValueError, TypeError):
            return FormTemplateType.OTHER


class FormField(Base):
    """表单字段定义"""
    __tablename__ = "form_fields"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("form_templates.id"), nullable=False)
    field_key = Column(String(100), nullable=False)  # 字段标识
    field_label = Column(String(200), nullable=False)  # 显示名称
    field_type = Column(String(30), default=FormFieldType.TEXT.value)
    locator_type = Column(String(30), default=LocatorType.TABLE_CELL.value)
    locator_data = Column(JSON)  # 定位数据：{table_idx, row, col} 或 {bookmark} 或 {label_text, direction}
    required = Column(Boolean, default=True)
    llm_extract_hint = Column(Text)  # LLM提取提示
    default_value = Column(Text)
    options_json = Column(JSON)  # select类型的选项列表
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    template = relationship("FormTemplate", back_populates="fields")
    field_values = relationship("FormFillFieldValue", back_populates="field", cascade="all, delete-orphan")


class FormFillTask(Base):
    """表单填报任务"""
    __tablename__ = "form_fill_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("design_projects.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("form_templates.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"))  # 输入文档
    status = Column(String(30), default=FormFillStatus.PENDING.value, index=True)
    extracted_data_json = Column(JSON)  # LLM提取的原始数据
    confirmed_data_json = Column(JSON)  # 用户确认后的数据
    output_file_path = Column(String(500))  # 生成的文件路径
    output_filename = Column(String(255))
    error_message = Column(Text)
    progress = Column(Integer, default=0)  # 进度0-100
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # 关系
    project = relationship("DesignProject", back_populates="form_tasks")
    template = relationship("FormTemplate", back_populates="fill_tasks")
    document = relationship("Document")
    field_values = relationship("FormFillFieldValue", back_populates="task", cascade="all, delete-orphan")

    @property
    def status_enum(self):
        try:
            return FormFillStatus(self.status)
        except (ValueError, TypeError):
            return FormFillStatus.PENDING


class FormFillFieldValue(Base):
    """表单字段提取值"""
    __tablename__ = "form_fill_field_values"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("form_fill_tasks.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("form_fields.id"), nullable=False)
    extracted_value = Column(Text)  # LLM提取的值
    confirmed_value = Column(Text)  # 用户确认的值
    confidence = Column(Float)  # 置信度0-1
    source_page = Column(Integer)  # 来源页码
    source_section = Column(String(255))  # 来源章节
    source_text = Column(Text)  # 原文摘录
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    task = relationship("FormFillTask", back_populates="field_values")
    field = relationship("FormField", back_populates="field_values")
