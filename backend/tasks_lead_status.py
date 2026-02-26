"""
Lead status auto-update task.
Runs periodically to update user lead_status based on their email engagement.

Rules:
- HOT: User clicked a link in the last 7 days
- WARM: User opened an email but didn't click in the last 7 days
- COLD: User hasn't opened any emails in the last 14 days
- NEW: User has no email activity yet
"""

from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from .celery_app import celery_app
from .models import User, Event, EventTypeEnum, EmailSend, LeadStatusEnum, Contact, Lead
from .core.async_runner import run_async
from .core.db import task_context


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def update_lead_statuses(self) -> None:
    """
    Celery Beat task that runs periodically (e.g., every 6 hours) to update
    all user lead statuses based on their email engagement behavior.
    """
    
    async def _run() -> None:
        async with task_context() as db:
            async with db.begin():
                # Get all leads with their shadow users
                q_leads = await db.execute(
                    sa.select(Lead, User)
                    .join(Contact, Lead.contact_id == Contact.id)
                    .join(User, Contact.email == User.email)
                )
                results = q_leads.all()
                
                now = datetime.utcnow()
                seven_days_ago = now - timedelta(days=7)
                fourteen_days_ago = now - timedelta(days=14)
                
                for lead, user in results:
                    # Skip if already unsubscribed
                    if lead.lead_status == LeadStatusEnum.unsubscribed:
                        continue
                    
                    # Check for clicks in last 7 days
                    q_clicks = await db.execute(
                        sa.select(sa.func.count(Event.id))
                        .where(
                            Event.user_id == user.id,
                            Event.type == EventTypeEnum.CLICKED,
                            Event.created_at >= seven_days_ago
                        )
                    )
                    click_count = q_clicks.scalar_one() or 0
                    
                    if click_count > 0:
                        if lead.lead_status != LeadStatusEnum.hot:
                            old_status = lead.lead_status
                            lead.lead_status = LeadStatusEnum.hot
                            # Emit event for tracking
                            event = Event(
                                type="lead_status_changed",
                                user_id=user.id,
                                data={"old_status": str(old_status), "new_status": "hot"}
                            )
                            db.add(event)
                        continue
                    
                    # Check for opens in last 7 days
                    q_opens = await db.execute(
                        sa.select(sa.func.count(Event.id))
                        .where(
                            Event.user_id == user.id,
                            Event.type == EventTypeEnum.OPENED,
                            Event.created_at >= seven_days_ago
                        )
                    )
                    open_count = q_opens.scalar_one() or 0
                    
                    if open_count > 0:
                        if lead.lead_status != LeadStatusEnum.warm:
                            old_status = lead.lead_status
                            lead.lead_status = LeadStatusEnum.warm
                            event = Event(
                                type="lead_status_changed",
                                user_id=user.id,
                                data={"old_status": str(old_status), "new_status": "warm"}
                            )
                            db.add(event)
                        continue
                    
                    # Check if user has ANY email activity
                    q_any_activity = await db.execute(
                        sa.select(sa.func.count(Event.id))
                        .where(Event.user_id == user.id)
                    )
                    any_activity = q_any_activity.scalar_one() or 0
                    
                    if any_activity == 0:
                        # No activity at all - keep as new
                        if lead.lead_status != LeadStatusEnum.new:
                            lead.lead_status = LeadStatusEnum.new
                        continue
                    
                    # Check for any opens in last 14 days
                    q_recent_opens = await db.execute(
                        sa.select(sa.func.count(Event.id))
                        .where(
                            Event.user_id == user.id,
                            Event.type == EventTypeEnum.OPENED,
                            Event.created_at >= fourteen_days_ago
                        )
                    )
                    recent_opens = q_recent_opens.scalar_one() or 0
                    
                    if recent_opens == 0:
                        # No opens in 14 days - mark as cold
                        if lead.lead_status != LeadStatusEnum.cold:
                            old_status = lead.lead_status
                            lead.lead_status = LeadStatusEnum.cold
                            event = Event(
                                type="lead_status_changed",
                                user_id=user.id,
                                data={"old_status": str(old_status), "new_status": "cold"}
                            )
                            db.add(event)
    
    run_async(_run())


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def update_user_lead_status_on_event(self, user_id: str, event_type: str) -> None:
    """
    Update a single user's lead status immediately when an event occurs.
    Called from event creation to provide real-time status updates.
    """
    
    async def _run() -> None:
        async with task_context() as db:
            async with db.begin():
                q_user = await db.execute(
                    sa.select(User).where(User.id == user_id)
                )
                user = q_user.scalar_one_or_none()
                
                if not user:
                    return
                
                # Find lead via email
                q_lead = await db.execute(
                    sa.select(Lead)
                    .join(Contact, Lead.contact_id == Contact.id)
                    .where(Contact.email == user.email)
                )
                lead = q_lead.scalar_one_or_none()
                
                if not lead or lead.lead_status == LeadStatusEnum.unsubscribed:
                    return
                
                # Update based on event type
                if event_type == EventTypeEnum.CLICKED.value:
                    if lead.lead_status != LeadStatusEnum.hot:
                        lead.lead_status = LeadStatusEnum.hot
                
                elif event_type == EventTypeEnum.OPENED.value:
                    # Only upgrade to warm if not already hot
                    if lead.lead_status not in [LeadStatusEnum.hot, LeadStatusEnum.warm]:
                        lead.lead_status = LeadStatusEnum.warm
    
    run_async(_run())
