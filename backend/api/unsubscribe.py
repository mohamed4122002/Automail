from beanie.operators import In
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from ..models import Event, User, WorkflowInstance, EmailSend, EventTypeEnum

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


class UnsubscribeRequest(BaseModel):
    user_id: UUID
    email_send_id: Optional[UUID] = None
    reason: Optional[str] = None


@router.post("/{token}")
async def unsubscribe_via_token(
    token: UUID
):
    """
    Handle unsubscribe via unique token.
    """
    
    # Get the email send record
    email_send = await EmailSend.find_one(EmailSend.unsubscribe_token == str(token)) # Token is saved as str usually, but check type
    if not email_send:
        # Try UUID matching if UUID was stored
        email_send = await EmailSend.find_one(EmailSend.unsubscribe_token == token)
        
    if not email_send:
        raise HTTPException(status_code=404, detail="Invalid or expired unsubscribe token")
    
    # Get user
    user = await User.find_one(User.id == email_send.user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User associated with this token not found")
    
    # Check if already unsubscribed
    if user.lead_status == "unsubscribed":
        return {"status": "already_unsubscribed", "email": user.email}
    
    # Create unsubscribe event
    event = Event(
        type=EventTypeEnum.UNSUBSCRIBED,
        user_id=user.id,
        campaign_id=email_send.campaign_id,
        workflow_id=email_send.workflow_id,
        workflow_step_id=email_send.workflow_step_id,
        email_send_id=email_send.id,
        data={
            "timestamp": datetime.utcnow().isoformat(),
            "method": "token_link",
            "token": str(token)
        }
    )
    await event.insert()
    
    # Update user status
    user.lead_status = "unsubscribed"
    await user.save()
    
    # Stop all active workflow instances for this user
    active_instances = await WorkflowInstance.find(
        WorkflowInstance.user_id == user.id,
        In(WorkflowInstance.status, ["active", "waiting"])
    ).to_list()
    
    for instance in active_instances:
        instance.status = "stopped"
        instance.completed_at = datetime.utcnow()
        await instance.save()
    
    # Broadcast to WebSocket
    try:
        from ..api.realtime import broadcast_event
        await broadcast_event({
            "type": "event",
            "event_type": "unsubscribed",
            "user_id": str(user.id),
            "user_email": user.email,
            "timestamp": datetime.utcnow().isoformat()
        })
    except:
        pass
    
    return {
        "status": "success",
        "email": user.email,
        "message": "You have been successfully unsubscribed"
    }


@router.post("/api")
async def unsubscribe_via_api(
    request: UnsubscribeRequest
):
    """
    API endpoint to unsubscribe a user programmatically.
    Used by admin interfaces or batch operations.
    """
    
    # Get user
    user = await User.find_one(User.id == request.user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create unsubscribe event
    event = Event(
        type=EventTypeEnum.UNSUBSCRIBED,
        user_id=request.user_id,
        email_send_id=request.email_send_id,
        data={
            "timestamp": datetime.utcnow().isoformat(),
            "method": "api",
            "reason": request.reason
        }
    )
    await event.insert()
    
    # Update user status
    user.lead_status = "unsubscribed"
    await user.save()
    
    # Stop all active workflows
    active_instances = await WorkflowInstance.find(
        WorkflowInstance.user_id == request.user_id,
        In(WorkflowInstance.status, ["active", "waiting"])
    ).to_list()
    
    for instance in active_instances:
        instance.status = "stopped"
        instance.completed_at = datetime.utcnow()
        await instance.save()
    
    workflows_stopped = len(active_instances)
    
    return {
        "message": "User unsubscribed successfully",
        "user_id": str(request.user_id),
        "email": user.email,
        "workflows_stopped": workflows_stopped
    }


@router.get("/stats")
async def get_unsubscribe_stats(
    days: int = 30
):
    """Get unsubscribe statistics for dashboard metrics."""
    
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    
    # Total unsubscribes
    total_unsubscribes = await Event.find(
        Event.type == EventTypeEnum.UNSUBSCRIBED,
        Event.created_at >= since
    ).count()
    
    # Unsubscribe rate (unsubscribes / total sent)
    total_sent = await EmailSend.find(
        EmailSend.status == "sent",
        EmailSend.created_at >= since
    ).count()
    
    unsubscribe_rate = (total_unsubscribes / total_sent * 100) if total_sent > 0 else 0
    
    # Total users with unsubscribed status
    total_unsubscribed_users = await User.find(User.lead_status == "unsubscribed").count()
    
    return {
        "total_unsubscribes": total_unsubscribes,
        "unsubscribe_rate": round(unsubscribe_rate, 2),
        "total_unsubscribed_users": total_unsubscribed_users,
        "period_days": days
    }
