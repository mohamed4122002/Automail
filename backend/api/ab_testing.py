from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from ..db import get_db
from ..services.ab_testing import ABTestingService
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/ab-testing", tags=["ab-testing"])

@router.post("/tests")
async def create_ab_test(
    subject_a: str,
    subject_b: str,
    campaign_id: Optional[UUID] = None,
    workflow_step_id: Optional[UUID] = None,
    test_limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new A/B test for a campaign or workflow step."""
    service = ABTestingService(db)
    # Check if a test already exists for this campaign/step
    existing = await service.get_active_test(campaign_id, workflow_step_id)
    if existing:
        raise HTTPException(status_code=400, detail="An active A/B test already exists for this item.")
    
    return await service.create_test(subject_a, subject_b, campaign_id, workflow_step_id, test_limit)

@router.get("/stats/{variant_id}")
async def get_ab_test_stats(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get performance statistics for an A/B test."""
    service = ABTestingService(db)
    stats = await service.get_stats(variant_id)
    if not stats:
        raise HTTPException(status_code=404, detail="A/B test not found.")
    return stats

@router.get("/active")
async def get_active_tests(
    campaign_id: Optional[UUID] = None,
    workflow_step_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get active A/B tests."""
    service = ABTestingService(db)
    test = await service.get_active_test(campaign_id, workflow_step_id)
    if not test:
        return {"status": "no_active_test"}
    return await service.get_stats(test.id)
