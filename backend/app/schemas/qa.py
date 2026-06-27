from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class QARequest(BaseModel):
    question: str
    scenario_type: Optional[str] = "standard"
    top_k: int = 5


class QASource(BaseModel):
    file_name: str
    page_number: Optional[int]
    section_title: Optional[str]
    text: str
    score: float


class QAResponse(BaseModel):
    answer: str
    sources: List[QASource] = []
    scenario_type: str


class QAFeedback(BaseModel):
    log_id: int
    feedback: str


class QALogResponse(BaseModel):
    id: int
    question: str
    answer: str
    scenario_type: Optional[str]
    feedback: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
