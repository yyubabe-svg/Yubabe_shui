import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class FileType(str, enum.Enum):
    STANDARD = "水利规范"
    PROJECT_REPORT = "历史工程报告"
    FLOOD_PLAN = "防汛预案"
    DESIGN_DOC = "设计说明书"
    REVIEW_OPINION = "审查意见"
    OTHER = "其他"


class SecurityLevel(str, enum.Enum):
    PUBLIC = "公开"
    INTERNAL = "内部"
    CONFIDENTIAL = "敏感"


class ParseStatus(str, enum.Enum):
    PENDING = "待解析"
    PARSING = "解析中"
    COMPLETED = "已完成"
    FAILED = "失败"


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    file_type = Column(String(50), default=FileType.OTHER.value)
    project_name = Column(String(255))
    river_basin = Column(String(100))
    department = Column(String(100))
    security_level = Column(String(50), default=SecurityLevel.INTERNAL.value)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255))
    file_size = Column(Integer)
    upload_user = Column(String(100))
    parse_status = Column(String(50), default=ParseStatus.PENDING.value)
    chunk_count = Column(Integer, default=0)
    metadata_json = Column(JSON)
    project_id = Column(Integer, ForeignKey("design_projects.id"), nullable=True)  # 关联项目
    chapter_json = Column(JSON)  # 章节结构JSON
    table_count = Column(Integer, default=0)  # 表格数量
    total_pages = Column(Integer, default=0)  # 总页数
    is_report = Column(Boolean, default=False)  # 是否标记为主报告
    is_expert_opinion = Column(Boolean, default=False)  # 是否标记为专家意见
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    project = relationship("DesignProject", back_populates="documents", foreign_keys=[project_id])

    @property
    def file_type_enum(self):
        try:
            return FileType(self.file_type)
        except (ValueError, TypeError):
            return FileType.OTHER

    @property
    def security_level_enum(self):
        try:
            return SecurityLevel(self.security_level)
        except (ValueError, TypeError):
            return SecurityLevel.INTERNAL

    @property
    def parse_status_enum(self):
        try:
            return ParseStatus(self.parse_status)
        except (ValueError, TypeError):
            return ParseStatus.PENDING


class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer)  # 块序号
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer)
    section_title = Column(String(255))
    chapter_path = Column(String(100))  # 章节编号路径 如 "3.2.1"
    embedding_id = Column(String(100))
    tables_json = Column(JSON)  # 块内表格结构化数据
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")
