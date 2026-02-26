from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from ..db import get_db
from ..services.analytics import AnalyticsService
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard_analytics(
    workflow_id: Optional[UUID] = Query(None, description="Filter by workflow ID"),
    campaign_id: Optional[UUID] = Query(None, description="Filter by campaign ID"),
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get dashboard analytics with optional workflow/campaign filtering.
    
    Query Parameters:
    - workflow_id: Filter results by specific workflow
    - campaign_id: Filter results by specific campaign
    - days: Number of days to look back (default: 30)
    """
    service = AnalyticsService(db)
    return await service.get_dashboard_stats(
        owner_id=user_id,
        workflow_id=workflow_id,
        campaign_id=campaign_id,
        days=days
    )


@router.get("/workflows/compare")
async def compare_workflows(
    workflow_ids: List[UUID] = Query(..., description="List of workflow IDs to compare"),
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Compare multiple workflows side-by-side.
    
    Query Parameters:
    - workflow_ids: Comma-separated list of workflow UUIDs
    - days: Number of days to look back (default: 30)
    
    Example: /analytics/workflows/compare?workflow_ids=uuid1&workflow_ids=uuid2
    """
    service = AnalyticsService(db)
    return await service.compare_workflows(
        owner_id=user_id,
        workflow_ids=workflow_ids,
        days=days
    )


@router.get("/workflows/{workflow_id}/performance")
async def get_workflow_performance(
    workflow_id: UUID,
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get detailed performance metrics for a specific workflow.
    
    Includes:
    - Total instances
    - Completion rate
    - Email statistics
    - Time-series chart data
    """
    service = AnalyticsService(db)
    return await service.get_workflow_performance(
        owner_id=user_id,
        workflow_id=workflow_id,
        days=days
    )


@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: UUID,
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get analytics for a specific campaign.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard_stats(
        owner_id=user_id,
        campaign_id=campaign_id,
        days=days
    )


@router.get("/reputation")
async def get_sender_reputation(
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get the sender's reputation score and diagnostic warnings.
    """
    service = AnalyticsService(db)
    return await service.get_sender_reputation(
        owner_id=user_id,
        days=days
    )
