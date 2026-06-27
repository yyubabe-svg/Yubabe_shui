from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChunkResponse(BaseModel):
    id: int
    chunk_text: str
    page_number: Optional[int]
    section_title: Optional[str]
    
    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: int
    title: str
    file_type: str
    project_name: Optional[str]
    river_basin: Optional[str]
    department: Optional[str]
    security_level: str
    original_filename: Optional[str]
    file_size: Optional[int]
    upload_user: Optional[str]
    parse_status: str
    chunk_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentDetail(DocumentResponse):
    chunks: List[ChunkResponse] = []
    
    class Config:
        from_attributes = True


class DocumentUpload(BaseModel):
    title: str
    file_type: str
    project_name: Optional[str] = None
    river_basin: Optional[str] = None
    department: Optional[str] = None
    security_level: str = "内部"
