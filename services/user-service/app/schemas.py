"""
User Service Pydantic Schemas.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Dict, Any, Optional

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    preferences: Optional[Dict[str, Any]] = {}

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    created_at: datetime
    preferences: Dict[str, Any]

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    preferences: Dict[str, Any]
