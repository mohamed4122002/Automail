from beanie.operators import In
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from ..models import Campaign, EmailSend, EmailRetryAttempt, Event, User
from ..schemas.retries import RetryConfig, RetryStats, RetryAttemptDetail, ColdLeadResponse
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/campaigns", tags=["retries"])

@router.get("/{campaign_id}/retry-stats", response_model=RetryStats)
async def get_retry_stats(
    campaign_id: UUID
):
    """Get retry statistics for a campaign."""
    
    # Total sent
    total_sent = await EmailSend.find(
        EmailSend.campaign_id == campaign_id,
        EmailSend.status == "sent"
    ).count()
    
    # Total unopened (sent but no open event)
    sends = await EmailSend.find(
        EmailSend.campaign_id == campaign_id,
        EmailSend.status == "sent"
    ).to_list()
    
    send_ids = [s.id for s in sends]
    
    opened_events = await Event.find(
        In(Event.email_send_id, send_ids),
        Event.type == "opened"
    ).to_list()
    
    opened_send_ids = {e.email_send_id for e in opened_events}
    total_unopened = len([s for s in sends if s.id not in opened_send_ids])
    
    # Pending retries
    pending_first_retry = await EmailRetryAttempt.find(
        EmailRetryAttempt.campaign_id == campaign_id,
        EmailRetryAttempt.attempt_number == 1,
        EmailRetryAttempt.status == "pending"
    ).count()
    
    pending_second_retry = await EmailRetryAttempt.find(
        EmailRetryAttempt.campaign_id == campaign_id,
        EmailRetryAttempt.attempt_number == 2,
        EmailRetryAttempt.status == "pending"
    ).count()
    
    # Marked as cold
    all_users = await User.find(User.lead_status == "cold").to_list()
    cold_user_ids = [u.id for u in all_users]
    
    marked_as_cold = await EmailSend.find(
        EmailSend.campaign_id == campaign_id,
        In(EmailSend.user_id, cold_user_ids)
    ).count()
    
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
    user_id: UUID = Depends(get_current_user_id)
):
    """Update retry configuration for a campaign."""
    
    campaign = await Campaign.find_one(Campaign.id == campaign_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign.retry_config = config.model_dump()
    await campaign.save()
    
    return {"message": "Retry configuration updated", "config": campaign.retry_config}


@router.get("/{campaign_id}/retry-attempts", response_model=list[RetryAttemptDetail])
async def list_retry_attempts(
    campaign_id: UUID
):
    """List all retry attempts for a campaign."""
    
    attempts = await EmailRetryAttempt.find(
        EmailRetryAttempt.campaign_id == campaign_id
    ).sort("-created_at").limit(100).to_list()
    
    user_ids = list(set([a.user_id for a in attempts]))
    users = await User.find(In(User.id, user_ids)).to_list()
    user_email_map = {u.id: u.email for u in users}
    
    return [
        RetryAttemptDetail(
            id=attempt.id,
            email_send_id=attempt.email_send_id,
            user_id=attempt.user_id,
            user_email=user_email_map.get(attempt.user_id, ""),
            attempt_number=attempt.attempt_number,
            scheduled_for=attempt.scheduled_for,
            status=attempt.status,
            created_at=attempt.created_at
        )
        for attempt in attempts
    ]


# Cold Leads endpoint (separate router for users)
cold_leads_router = APIRouter(prefix="/users", tags=["cold-leads"])

@cold_leads_router.get("/cold-leads", response_model=list[ColdLeadResponse])
async def get_cold_leads():
    """Get all users marked as cold leads."""
    
    cold_users = await User.find(User.lead_status == "cold").sort("-updated_at").to_list()
    user_ids = [u.id for u in cold_users]
    
    sends = await EmailSend.find(In(EmailSend.user_id, user_ids)).to_list()
    retries = await EmailRetryAttempt.find(In(EmailRetryAttempt.user_id, user_ids)).to_list()
    
    last_send_map = {}
    for s in sends:
        if s.user_id not in last_send_map or s.created_at > last_send_map[s.user_id]:
            last_send_map[s.user_id] = s.created_at
            
    retry_count_map = {}
    for r in retries:
        retry_count_map[r.user_id] = retry_count_map.get(r.user_id, 0) + 1
    
    return [
        ColdLeadResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            last_email_sent=last_send_map.get(user.id, user.created_at),
            retry_attempts=retry_count_map.get(user.id, 0),
            marked_cold_at=user.updated_at
        )
        for user in cold_users
    ]
