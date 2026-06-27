from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from app.core.database import Base


class ReviewReport(Base):
    __tablename__ = "review_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    file_name = Column(String(255))
    extracted_params_json = Column(JSON)
    issues_json = Column(JSON)
    suggestions_json = Column(JSON)
    sources_json = Column(JSON)
    review_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
