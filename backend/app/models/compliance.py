"""
合规初审模块数据模型
包含：初审项目、检查表模板、检查项、初审记录、初审意见、附件
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ComplianceProject(Base):
    """合规初审项目表"""
    __tablename__ = "compliance_projects"

    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(100), unique=True, index=True, nullable=False, comment="项目编号")
    project_name = Column(String(500), nullable=False, comment="项目名称")
    project_type = Column(String(100), comment="项目类型：堤防/水库/灌溉/供水/发电等")
    project_stage = Column(String(50), comment="项目阶段：建议书/可研/初设/施工图等")
    applicant = Column(String(100), comment="申报单位/申报人")
    applicant_dept = Column(String(200), comment="申报部门")
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审核人ID")
    reviewer_name = Column(String(100), comment="审核人姓名")
    status = Column(String(50), default="draft", comment="状态：draft草稿/submitted已待审/reviewing审核中/returned退回/passed通过/rejected不通过")
    priority = Column(String(20), default="normal", comment="优先级：low/normal/high/urgent")
    total_score = Column(Float, default=0, comment="初审得分")
    pass_score = Column(Float, default=60, comment="及格分数线")
    conclusion = Column(String(50), comment="审核结论：通过/有条件通过/不通过")
    summary = Column(Text, comment="初审总结")
    submitted_at = Column(DateTime(timezone=True), comment="提交时间")
    reviewed_at = Column(DateTime(timezone=True), comment="审核完成时间")
    deadline = Column(DateTime(timezone=True), comment="审核截止时间")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系
    reviews = relationship("ComplianceReview", back_populates="project", cascade="all, delete-orphan")
    checklists = relationship("ComplianceChecklistInstance", back_populates="project", cascade="all, delete-orphan")
    attachments = relationship("ComplianceAttachment", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("ComplianceComment", back_populates="project", cascade="all, delete-orphan")


class ComplianceChecklistTemplate(Base):
    """检查表模板表"""
    __tablename__ = "compliance_checklist_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_code = Column(String(50), unique=True, index=True, comment="模板编码")
    template_name = Column(String(200), nullable=False, comment="模板名称")
    template_type = Column(String(50), comment="适用项目类型")
    template_stage = Column(String(50), comment="适用项目阶段")
    description = Column(Text, comment="模板说明")
    version = Column(String(20), default="1.0", comment="版本号")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系
    items = relationship("ComplianceCheckItem", back_populates="template", cascade="all, delete-orphan")


class ComplianceCheckItem(Base):
    """检查项表"""
    __tablename__ = "compliance_check_items"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("compliance_checklist_templates.id"), nullable=False)
    category = Column(String(100), comment="检查类别：资质文件/技术文件/审批流程/法律法规/其他")
    item_code = Column(String(50), comment="检查项编码")
    item_name = Column(String(500), nullable=False, comment="检查项名称")
    item_description = Column(Text, comment="检查项说明")
    check_standard = Column(Text, comment="检查标准/依据")
    check_method = Column(String(200), comment="检查方式：文件审查/现场核查/系统核验")
    weight = Column(Float, default=1.0, comment="权重")
    score = Column(Float, default=10, comment="该项满分")
    is_required = Column(Boolean, default=True, comment="是否必查项")
    risk_level = Column(String(20), default="medium", comment="风险等级：low/medium/high/critical")
    reference_docs = Column(JSON, comment="参考法规/标准文档列表")
    sort_order = Column(Integer, default=0, comment="排序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    template = relationship("ComplianceChecklistTemplate", back_populates="items")


class ComplianceChecklistInstance(Base):
    """检查表实例表（项目关联的检查表）"""
    __tablename__ = "compliance_checklist_instances"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("compliance_projects.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("compliance_checklist_templates.id"), nullable=False)
    template_name = Column(String(200), comment="模板名称（快照）")
    total_items = Column(Integer, default=0, comment="总检查项数")
    completed_items = Column(Integer, default=0, comment="已完成项数")
    passed_items = Column(Integer, default=0, comment="通过项数")
    failed_items = Column(Integer, default=0, comment="不通过项数")
    warning_items = Column(Integer, default=0, comment="警告项数")
    total_score = Column(Float, default=0, comment="实际得分")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    project = relationship("ComplianceProject", back_populates="checklists")
    review_items = relationship("ComplianceReviewItem", back_populates="checklist", cascade="all, delete-orphan")


class ComplianceReviewItem(Base):
    """初审项审核记录表"""
    __tablename__ = "compliance_review_items"

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("compliance_checklist_instances.id"), nullable=False)
    check_item_id = Column(Integer, ForeignKey("compliance_check_items.id"), nullable=False)
    category = Column(String(100), comment="检查类别（快照）")
    item_name = Column(String(500), comment="检查项名称（快照）")
    check_standard = Column(Text, comment="检查标准（快照）")
    result = Column(String(20), comment="审核结果：pass通过/fail不通过/warning警告/na不适用")
    score = Column(Float, default=0, comment="实际得分")
    issue_description = Column(Text, comment="问题描述")
    rectification_suggestion = Column(Text, comment="整改建议")
    evidence = Column(JSON, comment="佐证材料：文件路径/截图等")
    reviewer_note = Column(Text, comment="审核人备注")
    reviewed_by = Column(Integer, nullable=True, comment="审核人ID")
    reviewed_at = Column(DateTime(timezone=True), comment="审核时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    checklist = relationship("ComplianceChecklistInstance", back_populates="review_items")


class ComplianceReview(Base):
    """初审记录表（审核流程记录）"""
    __tablename__ = "compliance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("compliance_projects.id"), nullable=False)
    review_round = Column(Integer, default=1, comment="审核轮次")
    action = Column(String(50), comment="操作：submit提交/assign分配/review审核/return退回/pass通过/reject不通过")
    operator_id = Column(Integer, nullable=True, comment="操作人ID")
    operator_name = Column(String(100), comment="操作人姓名")
    operator_dept = Column(String(200), comment="操作人部门")
    opinion = Column(Text, comment="审核意见")
    result_data = Column(JSON, comment="审核结果数据快照")
    attachments = Column(JSON, comment="操作附件")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    project = relationship("ComplianceProject", back_populates="reviews")


class ComplianceComment(Base):
    """初审意见/沟通记录表"""
    __tablename__ = "compliance_comments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("compliance_projects.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("compliance_comments.id"), nullable=True, comment="父评论ID（用于回复）")
    comment_type = Column(String(50), default="general", comment="类型：general一般意见/problem问题/rectification整改/reply回复")
    content = Column(Text, nullable=False, comment="评论内容")
    author_id = Column(Integer, nullable=True, comment="评论人ID")
    author_name = Column(String(100), comment="评论人姓名")
    author_dept = Column(String(200), comment="评论人部门")
    is_private = Column(Boolean, default=False, comment="是否仅内部可见")
    attachments = Column(JSON, comment="附件列表")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系
    project = relationship("ComplianceProject", back_populates="comments")
    replies = relationship("ComplianceComment", backref="parent", remote_side=[id])


class ComplianceAttachment(Base):
    """附件表"""
    __tablename__ = "compliance_attachments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("compliance_projects.id"), nullable=False)
    file_name = Column(String(500), nullable=False, comment="文件名")
    file_path = Column(String(1000), nullable=False, comment="文件路径")
    file_type = Column(String(50), comment="文件类型：申报文件/资质证明/技术资料/审核报告/其他")
    file_size = Column(Integer, comment="文件大小（字节）")
    mime_type = Column(String(100), comment="MIME类型")
    category = Column(String(100), comment="附件分类")
    uploader_id = Column(Integer, nullable=True, comment="上传人ID")
    uploader_name = Column(String(100), comment="上传人姓名")
    description = Column(Text, comment="附件说明")
    is_required = Column(Boolean, default=False, comment="是否必备文件")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    project = relationship("ComplianceProject", back_populates="attachments")
