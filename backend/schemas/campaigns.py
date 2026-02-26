from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from .base import IDSchema, TimestampSchema

class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = False
    contact_list_id: Optional[UUID] = None
    warmup_config: Optional[dict] = {
        "enabled": False,
        "initial_volume": 10,
        "daily_increase_pct": 10.0,
        "max_volume": 1000,
        "current_limit": 10
    }

class CampaignCreate(CampaignBase):
    pass

class CampaignStats(BaseModel):
    sent: int
    open_rate: str # e.g. "45%"
    click_rate: str # e.g. "12%"

class WorkflowSimple(BaseModel):
    id: UUID
    name: str
    is_active: bool
    
    class Config:
        from_attributes = True

class CampaignOut(CampaignBase, IDSchema, TimestampSchema):
    owner_id: UUID
    warmup_last_limit_increase: Optional[datetime] = None
    workflow: Optional[WorkflowSimple] = None # Update to use proper schema

class CampaignList(CampaignBase, IDSchema, TimestampSchema):
    owner_id: UUID
    stats: CampaignStats
    status: str # active, paused, draft, etc.

class Recipient(BaseModel):
    id: UUID
    email: str
    status: str # opened, clicked, sent
    last_activity: str | datetime

class CampaignDetail(CampaignList):
    overview_stats: List[dict] # Detailed stats for cards
    recipients: List[Recipient]
    warmup_config: Optional[dict] = None
    workflow: Optional[WorkflowSimple] = None # Update to use proper schema
