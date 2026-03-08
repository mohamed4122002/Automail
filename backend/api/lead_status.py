from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pydantic import BaseModel

from ..models import User, Contact, Lead, LeadStatusEnum
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
async def get_lead_status_distribution():
    """Get count of users by lead status."""
    
    leads = await Lead.find_all().to_list()
    
    distribution = {
        LeadStatusEnum.hot.value: 0,
        LeadStatusEnum.warm.value: 0,
        LeadStatusEnum.cold.value: 0,
        LeadStatusEnum.new.value: 0,
        LeadStatusEnum.unsubscribed.value: 0
    }
    
    for lead in leads:
        status_val = lead.lead_status.value if hasattr(lead.lead_status, 'value') else str(lead.lead_status)
        # normalize to lower string to match enum values
        status_val = status_val.lower() if isinstance(status_val, str) else status_val
        if status_val in distribution:
            distribution[status_val] += 1
    
    return LeadStatusDistribution(**distribution)


@router.put("/{user_id}/lead-status")
async def update_user_lead_status(
    user_id: UUID,
    request: UpdateLeadStatusRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Manually update a user's lead status."""
    
    try:
        new_status = LeadStatusEnum(request.lead_status.lower())
    except ValueError:
        valid_statuses = [s.value for s in LeadStatusEnum]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid lead status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    contact = await Contact.find_one(Contact.email == user.email)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    lead = await Lead.find_one(Lead.contact_id == contact.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    old_status = lead.lead_status
    lead.lead_status = new_status
    await lead.save()
    
    return {
        "message": "Lead status updated",
        "user_id": str(user_id),
        "old_status": old_status.value if hasattr(old_status, 'value') else str(old_status),
        "new_status": new_status.value if hasattr(new_status, 'value') else str(new_status)
    }


@router.post("/lead-status/refresh-all")
async def refresh_all_lead_statuses():
    """Trigger immediate refresh of all user lead statuses."""
    from ..tasks_lead_status import update_lead_statuses
    
    # Queue the task
    update_lead_statuses.apply_async()
    
    return {
        "message": "Lead status refresh queued",
        "status": "processing"
    }
