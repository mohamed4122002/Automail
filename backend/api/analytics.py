from fastapi import APIRouter, Depends, Query
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from ..services.analytics import AnalyticsService
from ..schemas.analytics import PerformanceStats, TargetProgress, CRMTargetCreate, CRMTargetResponse, DashboardResponse
from ..models import CRMTarget
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user_id: Optional[UUID] = None,
    campaign_id: Optional[UUID] = None,
    workflow_id: Optional[UUID] = None,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Unified dashboard endpoint for stats, charts, and activity.
    """
    # If no user_id filter provided, default to current user if not admin
    # (Implementation detail: for now we just pass through)
    return await AnalyticsService.get_dashboard_data(user_id, campaign_id, workflow_id)

@router.get("/performance", response_model=PerformanceStats)
async def get_performance(
    user_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get performance statistics for a specific user or overall.
    """
    return await AnalyticsService.get_performance_stats(user_id, start_date, end_date)

@router.get("/targets", response_model=TargetProgress)
async def get_targets(
    month: Optional[str] = None,
    user_id: Optional[UUID] = None,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get target progress. Defaults to current month if not specified.
    """
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    return await AnalyticsService.get_target_progress(month, user_id)

@router.post("/targets", response_model=CRMTargetResponse)
async def create_target(
    target: CRMTargetCreate,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Set/Update a target for a month. Admin only in production (role check should be added).
    """
    # Check if target already exists for this month/user
    existing = await CRMTarget.find_one(CRMTarget.month == target.month, CRMTarget.user_id == target.user_id)
    
    if existing:
        existing.revenue_target = target.revenue_target
        existing.calls_target = target.calls_target
        existing.proposals_target = target.proposals_target
        existing.meetings_target = target.meetings_target
        await existing.save()
        return existing
    
    new_target = CRMTarget(**target.model_dump())
    await new_target.insert()
    return new_target

@router.get("/targets/all", response_model=List[CRMTargetResponse])
async def list_targets(
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List all targets.
    """
    return await CRMTarget.find_all().to_list()
