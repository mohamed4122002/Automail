from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from ..api.deps import get_current_user_id, get_current_user
from ..schemas.analytics import ActionCenterResponse, TargetProgress
from ..models import Lead, CRMLeadStage, Organization, CRMActivity, ActivityType, UserRole, User, Event, EventTypeEnum
from ..cache import cache_get, cache_set, delete_cache

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ─── CRM Target Progress ──────────────────────────────────────────────────

@router.get("/targets", response_model=TargetProgress)
async def get_target_progress(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get progress against CRM targets for the current month.
    """
    from ..services.analytics import AnalyticsService
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")
        
    user_id = None
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        user_id = current_user.id
        
    return await AnalyticsService.get_target_progress(month, user_id)

# ─── Sender Reputation ─────────────────────────────────────────────────────

@router.get("/reputation")
async def get_reputation(
    current_user: User = Depends(get_current_user)
):
    """
    Get sender reputation metrics and status.
    """
    # In a real implementation, this would aggregate from metrics
    # For now, we calculate from recent events or mock
    total_sent = await Event.find(Event.type == EventTypeEnum.SENT).count()
    if total_sent == 0:
        return {
            "score": 100,
            "status": "EXCELLENT",
            "metrics": {
                "total_emails_sent": 0,
                "open_rate": 0,
                "click_rate": 0,
                "bounce_rate": 0,
                "unsubscribe_rate": 0
            },
            "warnings": []
        }

    bounced = await Event.find(Event.type == EventTypeEnum.BOUNCED).count()
    opened = await Event.find(Event.type == EventTypeEnum.OPENED).count()
    clicked = await Event.find(Event.type == EventTypeEnum.CLICKED).count()
    unsubbed = await Event.find(Event.type == EventTypeEnum.UNSUBSCRIBED).count()

    bounce_rate = round((bounced / total_sent * 100), 1)
    open_rate = round((opened / total_sent * 100), 1)
    click_rate = round((clicked / total_sent * 100), 1)
    unsub_rate = round((unsubbed / total_sent * 100), 1)

    score = 100 - (bounce_rate * 5) - (unsub_rate * 10)
    score = max(0, min(100, int(score)))

    status = "EXCELLENT"
    if score < 50: status = "POOR"
    elif score < 75: status = "GOOD"
    elif score < 90: status = "GREAT"

    warnings = []
    if bounce_rate > 5:
        warnings.append("High bounce rate detected. Clean your lead lists.")
    if unsub_rate > 2:
        warnings.append("Unsubscribe rate is above average. Review your content.")

    return {
        "score": score,
        "status": status,
        "metrics": {
            "total_emails_sent": total_sent,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "bounce_rate": bounce_rate,
            "unsubscribe_rate": unsub_rate
        },
        "warnings": warnings
    }

# ─── Organization Summary ──────────────────────────────────────────────────

class OrgSummaryResponse(BaseModel):
    lead_count: int
    total_deal_value: float
    won_deal_value: float
    last_activity_at: Optional[datetime]
    stage_breakdown: Dict[str, int]

@router.get("/organizations/{org_id}/summary", response_model=OrgSummaryResponse)
async def get_org_summary(
    org_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Returns aggregated stats for a specific organization."""
    # aggregate statistics directly in MongoDB
    agg_pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": "$stage",
            "count": {"$sum": 1},
            "total": {"$sum": {"$ifNull": ["$deal_value", 0]}},
            "won": {"$sum": {"$cond": [{"$in": ["$stage", ["won", "project"]]}, {"$ifNull": ["$deal_value", 0]}, 0]}}
        }},
        {"$sort": {"_id": 1}}
    ]
    raw = await Lead.get_motor_collection().aggregate(agg_pipeline).to_list(length=None)

    lead_count = 0
    total_deal_value = 0.0
    won_deal_value = 0.0
    last_activity_at = None
    stage_breakdown: Dict[str, int] = {}

    for entry in raw:
        stage_val = entry.get("_id")
        count = entry.get("count", 0)
        total = float(entry.get("total", 0))
        won = float(entry.get("won", 0))

        s = stage_val.value if hasattr(stage_val, "value") else str(stage_val)
        stage_breakdown[s] = count
        lead_count += count
        total_deal_value += total
        won_deal_value += won

    # last_activity_at still requires a separate query to find the max
    class LeadActivityProjection(BaseModel):
        last_activity_at: Optional[datetime] = None

    last_doc = await Lead.find(Lead.organization_id == org_id).sort("-last_activity_at").project(LeadActivityProjection).limit(1).to_list()
    if last_doc and hasattr(last_doc[0], "last_activity_at"):
        last_activity_at = last_doc[0].last_activity_at

    summary = OrgSummaryResponse(
        lead_count=lead_count,
        total_deal_value=total_deal_value,
        won_deal_value=won_deal_value,
        last_activity_at=last_activity_at,
        stage_breakdown=stage_breakdown
    )
    return summary
        
@router.get("/dashboard")
async def get_dashboard(
    workflow_id: Optional[UUID] = None,
    campaign_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user)
):
    """Fetch aggregated dashboard metrics and chart data. Cached 30 s per user."""
    from ..services.analytics import AnalyticsService
    user_id = None
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        user_id = current_user.id

    # ── Cache per-user (managers share one key) ────────────────────────────
    uid_key = str(user_id) if user_id else "all"
    CACHE_KEY = f"analytics:dashboard:{uid_key}"
    cached = await cache_get(CACHE_KEY)
    if cached:
        return cached
    # ───────────────────────────────────────────────────────────────────────

    result = await AnalyticsService.get_dashboard_data(
        user_id=user_id,
        workflow_id=workflow_id,
        campaign_id=campaign_id
    )
    await cache_set(CACHE_KEY, result, ttl=30)
    return result

@router.get("/action-center", response_model=ActionCenterResponse)
async def get_action_center(
    current_user: User = Depends(get_current_user)
):
    """Unified command center for tasks, leads, and notifications."""
    from ..services.analytics import AnalyticsService
    return await AnalyticsService.get_action_center_data(current_user)
