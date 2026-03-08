from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

# Lead Schemas
class LeadBase(BaseModel):
    company_name: str = "TBD"
    source: str = "Marketing"
    stage: str = "lead"
    assigned_to_id: Optional[UUID] = None
    lead_status: str = "new"
    lead_score: int = 0
    deal_value: float = 0.0

class LeadCreate(BaseModel):
    company_name: str
    source: str = "Marketing"
    contact_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    stage: Optional[str] = "lead"

class LeadUpdate(BaseModel):
    # CRM Lead fields
    company_name: Optional[str] = None
    source: Optional[str] = None
    stage: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    assigned_by_id: Optional[UUID] = None
    proposal_deadline: Optional[datetime] = None
    
    # Marketing Lead fields
    lead_status: Optional[str] = None
    lead_score: Optional[int] = None
    deal_value: Optional[float] = None
    last_contacted_at: Optional[datetime] = None
    
    # Contact fields
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    attributes: Optional[dict] = None

class LeadResponse(LeadBase):
    id: UUID
    contact_id: Optional[UUID] = None
    assigned_by_id: Optional[UUID] = None
    proposal_deadline: Optional[datetime] = None
    last_activity_at: datetime
    claimed_at: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    last_email_opened_at: Optional[datetime] = None
    last_link_clicked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Assigned user info
    assigned_to_email: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_by_email: Optional[str] = None
    assigned_by_name: Optional[str] = None

    class Config:
        from_attributes = True

class LeadStatsResponse(BaseModel):
    total: int
    by_stage: dict[str, int]
    by_status: dict[str, int]

class LeadActivityItem(BaseModel):
    id: UUID
    type: str  # 'email_sent', 'email_opened', 'link_clicked', 'status_changed', 'assigned', 'call', 'meeting'
    description: str
    created_at: datetime
    metadata: Optional[dict] = None
    source: Optional[str] = "System"

class LeadActivityResponse(BaseModel):
    lead_id: UUID
    activities: list[LeadActivityItem]

class ActivityCreate(BaseModel):
    type: str # 'call', 'meeting', 'note', 'email'
    content: str
    metadata: Optional[dict] = None

class TaskCreate(BaseModel):
    assigned_to_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    status: str
    completed_at: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: UUID
    lead_id: UUID
    assigned_to_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime
