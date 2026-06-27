"""
水利计算历史记录模型
存储用户在工作台中进行的计算记录，可复用和追溯
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class CalcHistory(Base):
    """水利计算历史记录"""
    __tablename__ = "calc_history"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("design_projects.id"), nullable=True, index=True)

    # 计算类型
    calc_type = Column(String(50), nullable=False, index=True)  # uniform_flow/storm_water_flow/...
    calc_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)  # 水力计算/排水管网/防洪/工程量

    # 输入输出
    input_params = Column(JSON, nullable=False)
    output_values = Column(JSON, nullable=False)
    calc_steps = Column(JSON, nullable=True)  # 计算过程
    code_basis = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    warnings = Column(JSON, nullable=True)

    # 用户标注
    label = Column(String(200), nullable=True)  # 用户自定义标签（如"K0+500断面"）
    is_favorite = Column(Integer, default=0)    # 是否收藏

    # 结果文件
    output_filename = Column(String(500), nullable=True)  # 导出的Excel/Word计算书

    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
