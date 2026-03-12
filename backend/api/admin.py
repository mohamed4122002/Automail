from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List, Optional
from ..models import User, UserRole, Setting, Lead, CRMLeadStage
from ..auth import get_current_admin, get_current_super_admin, get_current_user
from ..schemas.users import UserProfile, UserRoleUpdate, UserManagerUpdate
from ..schemas.utils import orm_list_to_pydantic, orm_to_pydantic
from ..cache import cache_get, cache_set
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=List[UserProfile])
async def list_all_users(
    role: Optional[UserRole] = None,
    admin: User = Depends(get_current_admin)
):
    """Admin-only: List all users, optionally filtered by role."""
    query = {}
    if role:
        query = {"role": role}
    
    # Force fresh fetch from DB
    users = await User.find(query).to_list()
    
    # Ensure role synchronization during list if any inconsistencies exist
    for user in users:
        if not user.roles and user.role:
            user.roles = [user.role.value]
            await user.save()
            
    return orm_list_to_pydantic(users, UserProfile)

@router.patch("/users/{user_id}/role", response_model=UserProfile)
async def update_user_role(
    user_id: UUID, 
    update: UserRoleUpdate, 
    admin: User = Depends(get_current_super_admin)
):
    """Super Admin-only: Update a user's role."""
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Preventing self-demotion
    if user.id == admin.id and update.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Super Admins cannot demote themselves"
        )
        
    try:
        new_role = UserRole(update.role)
        user.role = new_role
        
        # Sync roles list
        user.roles = [new_role.value]
        
        await user.save()
        return orm_to_pydantic(user, UserProfile)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {update.role}")

@router.patch("/users/{user_id}/manager", response_model=UserProfile)
async def update_user_manager(
    user_id: UUID,
    update: UserManagerUpdate,
    admin: User = Depends(get_current_super_admin)
):
    """Super Admin-only: Update a user's manager."""
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.manager_id = update.manager_id
    await user.save()
    return orm_to_pydantic(user, UserProfile)

@router.get("/business-stats")
async def get_business_stats(admin: User = Depends(get_current_admin)):
    """Admin-only: Get business-centric statistics and KPIs."""
    from ..models import Lead, Event, Campaign, EmailSend, LeadStatusEnum
    from datetime import datetime, timedelta, timezone
    
    # 1. Lead Funnel
    total_leads = await Lead.count()
    hot_leads = await Lead.find(Lead.lead_status == LeadStatusEnum.hot).count()
    warm_leads = await Lead.find(Lead.lead_status == LeadStatusEnum.warm).count()
    
    # 2. Aggregated Engagement (Campaign Pulse)
    total_sent = await Event.find({"type": "sent"}).count()
    total_opened = await Event.find({"type": "opened"}).count()
    total_clicked = await Event.find({"type": "clicked"}).count()
    
    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
    
    # 3. Team Productivity (Last 30 Days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    user_activity = []
    all_users = await User.find_all().to_list()
    
    for u in all_users:
        activity_count = await Event.find({
            "user_id": u.id,
            "created_at": {"$gte": thirty_days_ago}
        }).count()
        
        user_activity.append({
            "email": u.email,
            "name": f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email,
            "activity": activity_count,
            "role": u.role
        })
    
    return {
        "funnel": {
            "total": total_leads,
            "hot": hot_leads,
            "warm": warm_leads,
            "conversion_opportunity": hot_leads + warm_leads
        },
        "engagement": {
            "sent": total_sent,
            "open_rate": round(open_rate, 2),
            "click_rate": round(click_rate, 2)
        },
        "team": sorted(user_activity, key=lambda x: x['activity'], reverse=True)[:5]
    }

@router.get("/stats")
async def get_system_stats(admin: User = Depends(get_current_admin)):
    """Admin-only: Get high-level system statistics."""
    from ..models import Lead, Campaign, EmailSend
    
    user_count = await User.count()
    lead_count = await Lead.count()
    campaign_count = await Campaign.count()
    email_count = await EmailSend.count()
    
    return {
        "users": user_count,
        "leads": lead_count,
        "campaigns": campaign_count,
        "emails_sent": email_count,
    }

@router.get("/settings")
async def get_system_settings(admin: User = Depends(get_current_super_admin)):
    """Super Admin-only: View global system settings."""
    settings = await Setting.find_all().to_list()
    return settings

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

@router.get("/revenue-forecast", response_model=RevenueForecastResponse)
async def get_revenue_forecast(
    current_user: User = Depends(get_current_user)
):
    """
    Weighted revenue forecast based on lead stages.
    Restricted to Admins/Managers. Cached for 120 s.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Analytics restricted to management.")

    CACHE_KEY = "analytics:revenue_forecast"
    cached = await cache_get(CACHE_KEY)
    if cached:
        return RevenueForecastResponse(**cached)

    agg_pipeline = [
        {"$project": {"stage": 1, "deal_value": {"$ifNull": ["$deal_value", 0]}}},
        {"$group": {
            "_id": "$stage",
            "count": {"$sum": 1},
            "raw": {"$sum": "$deal_value"}
        }}
    ]
    raw_results = await Lead.get_motor_collection().aggregate(agg_pipeline).to_list(length=None)

    stage_data = {}
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
