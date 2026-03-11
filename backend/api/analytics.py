from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from ..api.deps import get_current_user_id, get_current_user
from ..schemas.analytics import ActionCenterResponse
from ..models import Lead, CRMLeadStage, Organization, CRMActivity, ActivityType, UserRole, User
from ..cache import cache_get, cache_set, delete_cache

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ─── Revenue Forecasting ───────────────────────────────────────────────────

class ForecastStage(BaseModel):
    stage: str
    raw_value: float
    weighted_value: float
    count: int

class RevenueForecastResponse(BaseModel):
    stages: List[ForecastStage]
    total_raw: float
    total_weighted: float
    currency: str = "USD"

STAGE_WEIGHTS = {
    CRMLeadStage.LEAD: 0.10,
    CRMLeadStage.CALL: 0.25,
    CRMLeadStage.MEETING: 0.50,
    CRMLeadStage.PROPOSAL: 0.75,
    CRMLeadStage.NEGOTIATION: 0.90,
    CRMLeadStage.WON: 1.0,
    CRMLeadStage.PROJECT: 1.0,
    CRMLeadStage.LOST: 0.0
}

@router.get("/admin/revenue-forecast", response_model=RevenueForecastResponse)
async def get_revenue_forecast(
    current_user: User = Depends(get_current_user)
):
    """
    Weighted revenue forecast based on lead stages.
    Restricted to Admins/Managers. Cached for 120 s.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Analytics restricted to management.")

    # ── Cache ──────────────────────────────────────────────────────────────
    CACHE_KEY = "analytics:revenue_forecast"
    cached = await cache_get(CACHE_KEY)
    if cached:
        return RevenueForecastResponse(**cached)
    # ───────────────────────────────────────────────────────────────────────

    # use aggregation to let Mongo handle the grouping logic
    agg_pipeline = [
        {"$project": {"stage": 1, "deal_value": {"$ifNull": ["$deal_value", 0]}}},
        {"$group": {
            "_id": "$stage",
            "count": {"$sum": 1},
            "raw": {"$sum": "$deal_value"}
        }}
    ]
    raw_results = await Lead.get_motor_collection().aggregate(agg_pipeline).to_list(length=None)

    stage_data: Dict[str, Dict[str, float]] = {}
    total_raw = 0.0
    total_weighted = 0.0

    for entry in raw_results:
        stage_val = entry.get("_id")
        count = entry.get("count", 0)
        raw_val = float(entry.get("raw", 0))
        weight = STAGE_WEIGHTS.get(stage_val, 0.0)
        weighted_val = raw_val * weight

        stage_str = stage_val.value if hasattr(stage_val, "value") else str(stage_val)
        stage_data[stage_str] = {"raw": raw_val, "weighted": weighted_val, "count": count}

        total_raw += raw_val
        total_weighted += weighted_val

    # sort by CRMLeadStage enum order
    order = [s.value for s in CRMLeadStage]
    sorted_stages = []
    for s_name in order:
        if s_name in stage_data:
            sorted_stages.append(ForecastStage(
                stage=s_name,
                raw_value=stage_data[s_name]["raw"],
                weighted_value=stage_data[s_name]["weighted"],
                count=stage_data[s_name]["count"]
            ))

    response = RevenueForecastResponse(
        stages=sorted_stages,
        total_raw=total_raw,
        total_weighted=total_weighted
    )
    await cache_set(CACHE_KEY, response.model_dump(), ttl=120)
    return response

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
    last_doc = await Lead.find(Lead.organization_id == org_id).sort("-last_activity_at").project("last_activity_at").limit(1).to_list()
    if last_doc and hasattr(last_doc[0], "last_activity_at"):
        last_activity_at = last_doc[0].last_activity_at

    summary = OrgSummaryResponse(
        lead_count=lead_count,
        total_deal_value=total_deal_value,
        won_deal_value=won_deal_value,
        last_activity_at=last_activity_at,
        stage_breakdown=stage_breakdown
    )
        
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
