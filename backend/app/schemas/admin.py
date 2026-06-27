from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class AdminStats(BaseModel):
    total_documents: int
    total_qa_today: int
    total_users: int
    documents_by_type: Dict[str, int]
    recent_uploads: List[Dict[str, Any]]
    recent_qa: List[Dict[str, Any]]


class ModelConfig(BaseModel):
    llm_provider: str
    llm_model: str
    embedding_provider: str
    mock_mode: bool
