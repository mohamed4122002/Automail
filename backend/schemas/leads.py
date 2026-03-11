from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
import enum


# Enum for Lead source - replaces free-text
class LeadSourceEnum(str, enum.Enum):
    marketing = "Marketing"
    referral = "Referral"
    cold_outreach = "Cold Outreach"
    inbound = "Inbound"
    website_form = "Website Form"
    organic_search = "Organic Search"
    social_media = "Social Media"
    conference = "Conference"
    other = "Other"


# Lead Schemas
class LeadBase(BaseModel):
    company_name: str = "TBD"
    source: str = "Marketing"
    stage: str = "lead"
    assigned_to_id: Optional[UUID] = None
    assigned_at: Optional[datetime] = None  # Phase 6
    assignment_type: Optional[str] = None  # Phase 6
    lead_status: str = "new"
    lead_score: int = 0
    deal_value: float = 0.0
    deal_currency: str = "USD"
    organization_id: Optional[UUID] = None


class LeadCreate(BaseModel):
    company_name: str
    source: LeadSourceEnum = LeadSourceEnum.marketing
    contact_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    stage: Optional[str] = "lead"

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v):
        """Accept both enum values and human-readable names."""
        if isinstance(v, LeadSourceEnum):
            return v
        # Try matching against enum values (e.g. "Marketing", "Referral")
        for member in LeadSourceEnum:
            if member.value.lower() == str(v).lower():
                return member
        # Try matching against enum keys
        try:
            return LeadSourceEnum[str(v).lower()]
        except KeyError:
            pass
        raise ValueError(
            f"Invalid source '{v}'. Must be one of: {[m.value for m in LeadSourceEnum]}"
        )


class LeadUpdate(BaseModel):
    # CRM Lead fields
    company_name: Optional[str] = None
    source: Optional[LeadSourceEnum] = None
    stage: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    assigned_by_id: Optional[UUID] = None
    proposal_deadline: Optional[datetime] = None

    # Marketing Lead fields
    lead_status: Optional[str] = None
    # NOTE: lead_score is intentionally EXCLUDED — it is now auto-calculated by the backend.
    deal_value: Optional[float] = None
    deal_currency: Optional[Literal["USD", "EGP", "EUR"]] = None
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
    deadline_reminder_sent: bool = False  # Phase 6
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
    type: str  # 'call', 'meeting', 'note', 'email'
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


class LeadScoreLogResponse(BaseModel):
    id: UUID
    lead_id: UUID
    event_type: str
    points: int
    note: Optional[str] = None
    created_at: datetime
