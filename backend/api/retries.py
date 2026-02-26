from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime, timedelta

from ..db import get_db
from ..models import Campaign, EmailSend, EmailRetryAttempt, Event, User
from ..schemas.retries import RetryConfig, RetryStats, RetryAttemptDetail, ColdLeadResponse
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/campaigns", tags=["retries"])

@router.get("/{campaign_id}/retry-stats", response_model=RetryStats)
async def get_retry_stats(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get retry statistics for a campaign."""
    
    # Total sent
    q_sent = await db.execute(
        select(func.count())
        .select_from(EmailSend)
        .where(
            EmailSend.campaign_id == campaign_id,
            EmailSend.status == "sent"
        )
    )
    total_sent = q_sent.scalar_one()
    
    # Total unopened (sent but no open event)
    q_unopened = await db.execute(
        select(func.count(func.distinct(EmailSend.id)))
        .select_from(EmailSend)
        .outerjoin(Event, (Event.email_send_id == EmailSend.id) & (Event.type == "opened"))
        .where(
            EmailSend.campaign_id == campaign_id,
            EmailSend.status == "sent",
            Event.id == None
        )
    )
    total_unopened = q_unopened.scalar_one()
    
    # Pending retries
    q_pending_first = await db.execute(
        select(func.count())
        .select_from(EmailRetryAttempt)
        .where(
            EmailRetryAttempt.campaign_id == campaign_id,
            EmailRetryAttempt.attempt_number == 1,
            EmailRetryAttempt.status == "pending"
        )
    )
    pending_first_retry = q_pending_first.scalar_one()
    
    q_pending_second = await db.execute(
        select(func.count())
        .select_from(EmailRetryAttempt)
        .where(
            EmailRetryAttempt.campaign_id == campaign_id,
            EmailRetryAttempt.attempt_number == 2,
            EmailRetryAttempt.status == "pending"
        )
    )
    pending_second_retry = q_pending_second.scalar_one()
    
    # Marked as cold
    q_cold = await db.execute(
        select(func.count())
        .select_from(User)
        .join(EmailSend, EmailSend.user_id == User.id)
        .where(
            EmailSend.campaign_id == campaign_id,
            User.lead_status == "cold"
        )
    )
    marked_as_cold = q_cold.scalar_one()
    
    return RetryStats(
        total_sent=total_sent,
        total_unopened=total_unopened,
        pending_first_retry=pending_first_retry,
        pending_second_retry=pending_second_retry,
        marked_as_cold=marked_as_cold
    )


@router.post("/{campaign_id}/configure-retries")
async def configure_retries(
    campaign_id: UUID,
    config: RetryConfig,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update retry configuration for a campaign."""
    
    q = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = q.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign.retry_config = config.model_dump()
    await db.commit()
    
    return {"message": "Retry configuration updated", "config": campaign.retry_config}


@router.get("/{campaign_id}/retry-attempts", response_model=list[RetryAttemptDetail])
async def list_retry_attempts(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all retry attempts for a campaign."""
    
    q = await db.execute(
        select(EmailRetryAttempt, User.email)
        .join(User, EmailRetryAttempt.user_id == User.id)
        .where(EmailRetryAttempt.campaign_id == campaign_id)
        .order_by(EmailRetryAttempt.created_at.desc())
        .limit(100)
    )
    results = q.all()
    
    return [
        RetryAttemptDetail(
            id=attempt.id,
            email_send_id=attempt.email_send_id,
            user_id=attempt.user_id,
            user_email=email,
            attempt_number=attempt.attempt_number,
            scheduled_for=attempt.scheduled_for,
            status=attempt.status,
            created_at=attempt.created_at
        )
        for attempt, email in results
    ]


# Cold Leads endpoint (separate router for users)
cold_leads_router = APIRouter(prefix="/users", tags=["cold-leads"])

@cold_leads_router.get("/cold-leads", response_model=list[ColdLeadResponse])
async def get_cold_leads(
    db: AsyncSession = Depends(get_db)
):
    """Get all users marked as cold leads."""
    
    q = await db.execute(
        select(User, func.max(EmailSend.created_at), func.count(EmailRetryAttempt.id))
        .outerjoin(EmailSend, EmailSend.user_id == User.id)
        .outerjoin(EmailRetryAttempt, EmailRetryAttempt.user_id == User.id)
        .where(User.lead_status == "cold")
        .group_by(User.id)
        .order_by(User.updated_at.desc())
    )
    results = q.all()
    
    return [
        ColdLeadResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            last_email_sent=last_sent or user.created_at,
            retry_attempts=retry_count or 0,
            marked_cold_at=user.updated_at
        )
        for user, last_sent, retry_count in results
    ]
