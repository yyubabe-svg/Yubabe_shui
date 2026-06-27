from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.core.database import Base


class QALog(Base):
    __tablename__ = "qa_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(100), index=True)  # 用户名（与UserUsage.name关联）
    question = Column(Text, nullable=False)
    answer = Column(Text)
    sources_json = Column(JSON)
    scenario_type = Column(String(50))
    feedback = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
