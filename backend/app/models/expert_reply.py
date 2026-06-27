import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReplyTaskStatus(str, enum.Enum):
    """回复任务状态"""
    PENDING = "pending"           # 待处理
    PARSING = "parsing"           # 意见解析中
    GENERATING = "generating"     # 回复生成中
    EDITING = "editing"           # 编辑中
    COMPLETED = "completed"       # 已完成
    EXPORTED = "exported"         # 已导出
    FAILED = "failed"             # 失败


class OpinionType(str, enum.Enum):
    """意见类型"""
    MODIFY = "modify"             # 修改类
    SUPPLEMENT = "supplement"     # 补充类
    EXPLAIN = "explain"           # 解释说明类
    OTHER = "other"               # 其他


class MajorCategory(str, enum.Enum):
    """专业分类"""
    HYDROLOGY = "hydrology"       # 水文
    GEOLOGY = "geology"           # 地质
    HYDRAULIC = "hydraulic"       # 水工
    CONSTRUCTION = "construction" # 施工
    INVESTMENT = "investment"     # 投资/概算
    SOIL_CONSERVATION = "soil_conservation"  # 水保
    ENVIRONMENT = "environment"   # 环境
    ELECTROMECHANICAL = "electromechanical"  # 机电金属结构
    RESETTLEMENT = "resettlement" # 移民占地
    FORMAT = "format"             # 格式/文字
    OTHER = "other"               # 其他


class ModifyStatus(str, enum.Enum):
    """修改状态"""
    MODIFIED = "已修改"
    SUPPLEMENTED = "已补充"
    EXPLAINED = "解释说明"
    NOT_MODIFIED = "不修改"


class ReplyStatus(str, enum.Enum):
    """回复状态"""
    DRAFT = "draft"               # 草稿
    CONFIRMED = "confirmed"       # 已确认


class ExpertReplyTask(Base):
    """专家意见回复任务"""
    __tablename__ = "expert_reply_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("design_projects.id"), nullable=False, index=True)
    opinion_document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)  # 意见文档
    report_document_id = Column(Integer, ForeignKey("documents.id"))  # 关联报告
    status = Column(String(30), default=ReplyTaskStatus.PENDING.value, index=True)
    meeting_name = Column(String(500))  # 审查会议名称
    meeting_date = Column(String(50))  # 审查日期
    expert_count = Column(Integer, default=0)  # 专家人数
    opinion_count = Column(Integer, default=0)  # 意见总数
    output_file_path = Column(String(500))
    output_filename = Column(String(255))
    error_message = Column(Text)
    progress = Column(Integer, default=0)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # 关系
    project = relationship("DesignProject", back_populates="expert_reply_tasks")
    opinion_document = relationship("Document", foreign_keys=[opinion_document_id])
    report_document = relationship("Document", foreign_keys=[report_document_id])
    opinions = relationship("ExpertOpinion", back_populates="reply_task", cascade="all, delete-orphan", order_by="ExpertOpinion.order_index")

    @property
    def status_enum(self):
        try:
            return ReplyTaskStatus(self.status)
        except (ValueError, TypeError):
            return ReplyTaskStatus.PENDING


class ExpertOpinion(Base):
    """单条专家意见"""
    __tablename__ = "expert_opinions"

    id = Column(Integer, primary_key=True, index=True)
    reply_task_id = Column(Integer, ForeignKey("expert_reply_tasks.id"), nullable=False, index=True)
    opinion_index = Column(Integer)  # 意见序号
    order_index = Column(Integer, default=0)  # 排序用
    expert_name = Column(String(100))  # 专家姓名
    major_category = Column(String(30))  # 专业分类
    opinion_type = Column(String(20))  # 意见类型
    content = Column(Text, nullable=False)  # 意见内容
    page_number = Column(Integer)  # 原文页码
    chapter_path = Column(String(200))  # 所在章节
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    reply_task = relationship("ExpertReplyTask", back_populates="opinions")
    reply_item = relationship("ExpertReplyItem", back_populates="opinion", uselist=False, cascade="all, delete-orphan")

    @property
    def major_category_name(self):
        mapping = {
            "hydrology": "水文", "geology": "地质", "hydraulic": "水工",
            "construction": "施工", "investment": "投资概算",
            "soil_conservation": "水土保持", "environment": "环境",
            "electromechanical": "机电金结", "resettlement": "移民占地",
            "format": "格式文字", "other": "其他"
        }
        return mapping.get(self.major_category, self.major_category or "其他")


class ExpertReplyItem(Base):
    """专家意见回复项"""
    __tablename__ = "expert_reply_items"

    id = Column(Integer, primary_key=True, index=True)
    opinion_id = Column(Integer, ForeignKey("expert_opinions.id"), nullable=False, unique=True, index=True)
    reply_content = Column(Text, nullable=False)  # 回复内容
    modify_status = Column(String(30), default=ModifyStatus.EXPLAINED.value)  # 修改状态
    modify_location = Column(String(200))  # 修改位置（页码/章节）
    modify_page = Column(String(50))  # 修改页号
    status = Column(String(20), default=ReplyStatus.DRAFT.value)
    sources_json = Column(JSON)  # 引用来源（规范条文、报告原文等）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    opinion = relationship("ExpertOpinion", back_populates="reply_item")
