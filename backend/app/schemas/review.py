from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ReviewParam(BaseModel):
    name: str
    value: Optional[str]
    location: Optional[str]


class ReviewIssue(BaseModel):
    category: str
    level: str
    description: str
    suggestion: str
    reference: Optional[str]


class ReviewAnalyzeRequest(BaseModel):
    file_path: str
    file_name: Optional[str] = None


class ReviewResponse(BaseModel):
    report_id: int
    project_name: Optional[str]
    params: List[ReviewParam]
    issues: List[ReviewIssue]
    suggestions: List[str]
    review_text: str
