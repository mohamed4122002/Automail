from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime

class PerformanceStats(BaseModel):
    revenue: float = 0.0
    calls: int = 0
    meetings: int = 0
    proposals: int = 0
    leads_won: int = 0
    leads_lost: int = 0
    conversion_rate: float = 0.0

class TargetProgress(BaseModel):
    month: str
    revenue: Dict[str, float]  # {"target": 1000, "achieved": 500}
    calls: Dict[str, int]
    proposals: Dict[str, int]
    meetings: Dict[str, int]
    overall_progress: float

class CRMTargetCreate(BaseModel):
    month: str
    user_id: Optional[UUID] = None
    revenue_target: float = 0.0
    calls_target: int = 0
    proposals_target: int = 0
    meetings_target: int = 0

class CRMTargetResponse(BaseModel):
    id: UUID
    month: str
    user_id: Optional[UUID] = None
    revenue_target: float = 0.0
    calls_target: int = 0
    proposals_target: int = 0
    meetings_target: int = 0
    created_at: datetime

class DashboardStats(BaseModel):
    total_emails_sent: int = 0
    sent_trend: float = 0.0
    open_rate: float = 0.0
    open_rate_trend: float = 0.0
    click_rate: float = 0.0
    click_rate_trend: float = 0.0
    pending_followups: int = 0
    pending_trend: float = 0.0

class DashboardResponse(BaseModel):
    stats: List[DashboardStats]
    chart_data: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]

class ActionCenterItem(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    type: str # 'task', 'lead_assignment', 'inactive_lead', 'notification'
    severity: str # 'high', 'medium', 'low'
    due_date: Optional[datetime] = None
    link: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ActionCenterResponse(BaseModel):
    actions: List[ActionCenterItem]
    counts: Dict[str, int]
    role: str

class ReputationMetrics(BaseModel):
    total_emails_sent: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    unsubscribe_rate: float = 0.0

class ReputationResponse(BaseModel):
    score: int
    status: str
    metrics: ReputationMetrics
    warnings: List[str] = Field(default_factory=list)
