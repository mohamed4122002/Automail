from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from .base import IDSchema, TimestampSchema

class UserNoteBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    content: str

class UserNoteCreate(UserNoteBase):
    pass

class UserNote(UserNoteBase, IDSchema, TimestampSchema):
    user_id: UUID
    created_by_id: Optional[UUID]

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    role: str = "team_member"
    roles: List[str] = []

class UserProfile(UserBase, IDSchema, TimestampSchema):
    model_config = ConfigDict(from_attributes=True)
    
    company: Optional[str] = "Unknown" 
    claimed_by_id: Optional[UUID] = None
    claimed_at: Optional[datetime] = None

class UserTimelineEvent(BaseModel):
    id: int | str | UUID
    type: str # 'sent', 'opened', 'clicked', 'note'
    content: str
    date: str | datetime
    icon_type: Optional[str] = None

class UserRoleUpdate(BaseModel):
    role: str
    roles: Optional[List[str]] = None

class UserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user: UserProfile
    timeline: List[UserTimelineEvent]
    notes: List[UserNote]

