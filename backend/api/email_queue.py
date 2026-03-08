from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from ..services.email_rate_limit import EmailRateLimitService
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/email-queue", tags=["email-queue"])


class RateLimitSettings(BaseModel):
    max_per_hour: int
    max_per_day: int
    enabled: bool


@router.get("/stats")
async def get_queue_stats(
    owner_id: UUID = Depends(get_current_user_id)
):
    """
    Get email queue statistics for dashboard widget.
    """
    service = EmailRateLimitService()
    return await service.get_queue_stats()


@router.get("/rate-limit-status")
async def get_rate_limit_status(
    owner_id: UUID = Depends(get_current_user_id)
):
    """Check if we can send more emails based on current rate limits."""
    service = EmailRateLimitService()
    can_send, reason = await service.check_rate_limit()
    
    return {
        "can_send": can_send,
        "reason": reason
    }


@router.post("/process-now")
async def process_queue_now(
    owner_id: UUID = Depends(get_current_user_id)
):
    """
    Manually trigger email queue processing.
    Useful for testing or immediate sending.
    """
    from ..tasks import process_email_queue
    
    # Trigger async task
    task = process_email_queue.delay()
    
    return {
        "message": "Queue processing triggered",
        "task_id": task.id
    }
