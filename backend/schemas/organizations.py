from pydantic import BaseModel, HttpUrl
from typing import Optional
from uuid import UUID
from datetime import datetime

class OrganizationBase(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None

class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
