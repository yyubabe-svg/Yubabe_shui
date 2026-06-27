from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    department: Optional[str] = None
    role: str = "user"


class UserResponse(BaseModel):
    id: int
    name: str
    username: str
    department: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
