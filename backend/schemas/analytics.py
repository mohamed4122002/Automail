from pydantic import BaseModel
from typing import List

class DashboardStats(BaseModel):
    total_emails_sent: int
    open_rate: float
    click_rate: float
    pending_followups: int
    # Trends (percentage change)
    sent_trend: float
    open_rate_trend: float
    click_rate_trend: float
    pending_trend: float

class ChartPoint(BaseModel):
    name: str # e.g. "Mon" or date string
    opens: int
    clicks: int

class ActivityLog(BaseModel):
    id: int | str
    user: str
    action: str
    time: str # relative time string e.g. "2 min ago" for frontend or isoform

class DashboardData(BaseModel):
    stats: List[dict] # mapped to StatsCard props structure if needed, or raw stats
    chart_data: List[ChartPoint]
    recent_activity: List[ActivityLog]
