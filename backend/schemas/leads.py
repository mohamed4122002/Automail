from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

# Lead Schemas
class LeadBase(BaseModel):
    lead_status: str
    lead_score: int = 0
    assigned_to_id: Optional[UUID] = None

class LeadCreate(LeadBase):
    contact_id: UUID

class LeadUpdate(BaseModel):
    # Lead fields
    lead_status: Optional[str] = None
    lead_score: Optional[int] = None
    assigned_to_id: Optional[UUID] = None
    last_contacted_at: Optional[datetime] = None
    
    # Contact fields
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact_list_id: Optional[UUID] = None
    attributes: Optional[dict] = None

class LeadResponse(LeadBase):
    id: UUID
    contact_id: UUID
    claimed_at: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    last_email_opened_at: Optional[datetime] = None
    last_link_clicked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Nested contact info
    contact_email: str
    contact_first_name: Optional[str] = None
    contact_last_name: Optional[str] = None
    contact_list_id: UUID
    contact_list_name: str
    
    # Assigned user info
    assigned_to_email: Optional[str] = None
    assigned_to_name: Optional[str] = None

    class Config:
        from_attributes = True

class LeadStatsResponse(BaseModel):
    total: int
    new: int
    warm: int
    hot: int
    cold: int
    unsubscribed: int
    by_list: dict[str, int]  # list_name -> count

class LeadActivityItem(BaseModel):
    id: UUID
    type: str  # 'email_sent', 'email_opened', 'link_clicked', 'status_changed', 'assigned'
    description: str
    created_at: datetime
    metadata: Optional[dict] = None

class LeadActivityResponse(BaseModel):
    lead_id: UUID
    activities: list[LeadActivityItem]
