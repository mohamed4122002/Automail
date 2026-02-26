from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from pydantic import BaseModel

from ..db import get_db
from ..models import User, LeadStatusEnum

from ..api.deps import get_current_user_id

router = APIRouter(prefix="/lead-status", tags=["lead-status"])

class LeadStatusDistribution(BaseModel):
    hot: int
    warm: int
    cold: int
    new: int
    unsubscribed: int

class UpdateLeadStatusRequest(BaseModel):
    lead_status: str

@router.get("/distribution", response_model=LeadStatusDistribution)
async def get_lead_status_distribution(db: AsyncSession = Depends(get_db)):
    """Get count of users by lead status."""
    
    q = await db.execute(
        select(User.lead_status, func.count(User.id))
        .group_by(User.lead_status)
    )
    results = q.all()
    
    distribution = {
        LeadStatusEnum.HOT.value: 0,
        LeadStatusEnum.WARM.value: 0,
        LeadStatusEnum.COLD.value: 0,
        LeadStatusEnum.NEW.value: 0,
        LeadStatusEnum.UNSUBSCRIBED.value: 0
    }
    
    for status, count in results:
        # status here will be an enum member due to Mapped[LeadStatusEnum]
        status_val = status.value if hasattr(status, 'value') else str(status)
        if status_val in distribution:
            distribution[status_val] = count
    
    return LeadStatusDistribution(**distribution)


@router.put("/{user_id}/lead-status")
async def update_user_lead_status(
    user_id: UUID,
    request: UpdateLeadStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Manually update a user's lead status."""
    
    try:
        new_status = LeadStatusEnum(request.lead_status)
    except ValueError:
        valid_statuses = [s.value for s in LeadStatusEnum]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid lead status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    q = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = q.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_status = user.lead_status
    user.lead_status = request.lead_status
    await db.commit()
    
    return {
        "message": "Lead status updated",
        "user_id": str(user_id),
        "old_status": old_status,
        "new_status": request.lead_status
    }


@router.post("/lead-status/refresh-all")
async def refresh_all_lead_statuses(db: AsyncSession = Depends(get_db)):
    """Trigger immediate refresh of all user lead statuses."""
    from ..tasks_lead_status import update_lead_statuses
    
    # Queue the task
    update_lead_statuses.apply_async()
    
    return {
        "message": "Lead status refresh queued",
        "status": "processing"
    }
