from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, List, Dict, Any
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from ..db import get_db
from ..models import Event, User, WorkflowInstance, EmailSend, EventTypeEnum

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


class UnsubscribeRequest(BaseModel):
    user_id: UUID
    email_send_id: Optional[UUID] = None
    reason: Optional[str] = None


@router.post("/{token}")
async def unsubscribe_via_token(
    token: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle unsubscribe via unique token.
    
    Actions:
    1. Find EmailSend record by token
    2. Create UNSUBSCRIBED event linked to user/campaign/workflow
    3. Update user lead_status to 'unsubscribed'
    4. Stop all active workflows for this user
    5. Broadcast event via WebSocket
    """
    
    # Get the email send record
    q_send = await db.execute(
        select(EmailSend).where(EmailSend.unsubscribe_token == token)
    )
    email_send = q_send.scalar_one_or_none()
    
    if not email_send:
        raise HTTPException(status_code=404, detail="Invalid or expired unsubscribe token")
    
    # Get user
    q_user = await db.execute(
        select(User).where(User.id == email_send.user_id)
    )
    user = q_user.scalar_one_or_none()
    
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
    db.add(event)
    
    # Update user status
    user.lead_status = "unsubscribed"
    
    # Stop all active workflow instances for this user
    await db.execute(
        update(WorkflowInstance)
        .where(
            WorkflowInstance.user_id == user.id,
            WorkflowInstance.status.in_(["active", "waiting"])
        )
        .values(
            status="stopped",
            completed_at=datetime.utcnow()
        )
    )
    
    await db.commit()
    
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
    request: UnsubscribeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    API endpoint to unsubscribe a user programmatically.
    Used by admin interfaces or batch operations.
    """
    
    # Get user
    q_user = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    user = q_user.scalar_one_or_none()
    
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
    db.add(event)
    
    # Update user status
    user.lead_status = "unsubscribed"
    
    # Stop all active workflows
    result = await db.execute(
        update(WorkflowInstance)
        .where(
            WorkflowInstance.user_id == request.user_id,
            WorkflowInstance.status.in_(["active", "waiting"])
        )
        .values(
            status="stopped",
            completed_at=datetime.utcnow()
        )
    )
    
    workflows_stopped = result.rowcount
    
    await db.commit()
    
    return {
        "message": "User unsubscribed successfully",
        "user_id": str(request.user_id),
        "email": user.email,
        "workflows_stopped": workflows_stopped
    }


@router.get("/stats")
async def get_unsubscribe_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get unsubscribe statistics for dashboard metrics."""
    
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    
    # Total unsubscribes
    q_total = await db.execute(
        select(func.count(Event.id))
        .where(
            Event.type == EventTypeEnum.UNSUBSCRIBED,
            Event.created_at >= since
        )
    )
    total_unsubscribes = q_total.scalar_one() or 0
    
    # Unsubscribe rate (unsubscribes / total sent)
    from ..models import EmailSend
    q_sent = await db.execute(
        select(func.count(EmailSend.id))
        .where(
            EmailSend.status == "sent",
            EmailSend.created_at >= since
        )
    )
    total_sent = q_sent.scalar_one() or 0
    
    unsubscribe_rate = (total_unsubscribes / total_sent * 100) if total_sent > 0 else 0
    
    # Total users with unsubscribed status
    q_users = await db.execute(
        select(func.count(User.id))
        .where(User.lead_status == "unsubscribed")
    )
    total_unsubscribed_users = q_users.scalar_one() or 0
    
    return {
        "total_unsubscribes": total_unsubscribes,
        "unsubscribe_rate": round(unsubscribe_rate, 2),
        "total_unsubscribed_users": total_unsubscribed_users,
        "period_days": days
    }
