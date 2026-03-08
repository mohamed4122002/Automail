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
import asyncio

from .celery_app import celery_app
from .models import User, Event, EventTypeEnum, LeadStatusEnum
from .core.async_runner import run_async


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
        users = await User.find_all().to_list()
        
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)
        
        for user in users:
            # Skip if already unsubscribed
            user_status = user.lead_status.value if hasattr(user.lead_status, 'value') else user.lead_status
            if user_status == LeadStatusEnum.UNSUBSCRIBED.value:
                continue
            
            # Check for clicks in last 7 days
            click_count = await Event.find(
                Event.user_id == user.id,
                Event.type == EventTypeEnum.CLICKED,
                Event.created_at >= seven_days_ago
            ).count()
            
            if click_count > 0:
                if user_status != LeadStatusEnum.HOT.value:
                    old_status = user_status
                    user.lead_status = LeadStatusEnum.HOT.value
                    await user.save()
                    # Emit event for tracking
                    event = Event(
                        type="lead_status_changed",
                        user_id=user.id,
                        data={"old_status": old_status, "new_status": "hot"}
                    )
                    await event.insert()
                continue
            
            # Check for opens in last 7 days
            open_count = await Event.find(
                Event.user_id == user.id,
                Event.type == EventTypeEnum.OPENED,
                Event.created_at >= seven_days_ago
            ).count()
            
            if open_count > 0:
                if user_status != LeadStatusEnum.WARM.value:
                    old_status = user_status
                    user.lead_status = LeadStatusEnum.WARM.value
                    await user.save()
                    event = Event(
                        type="lead_status_changed",
                        user_id=user.id,
                        data={"old_status": old_status, "new_status": "warm"}
                    )
                    await event.insert()
                continue
            
            # Check if user has ANY email activity
            any_activity = await Event.find(Event.user_id == user.id).count()
            
            if any_activity == 0:
                # No activity at all - keep as new
                if user_status != LeadStatusEnum.NEW.value:
                    user.lead_status = LeadStatusEnum.NEW.value
                    await user.save()
                continue
            
            # Check for any opens in last 14 days
            recent_opens = await Event.find(
                Event.user_id == user.id,
                Event.type == EventTypeEnum.OPENED,
                Event.created_at >= fourteen_days_ago
            ).count()
            
            if recent_opens == 0:
                # No opens in 14 days - mark as cold
                if user_status != LeadStatusEnum.COLD.value:
                    old_status = user_status
                    user.lead_status = LeadStatusEnum.COLD.value
                    await user.save()
                    event = Event(
                        type="lead_status_changed",
                        user_id=user.id,
                        data={"old_status": old_status, "new_status": "cold"}
                    )
                    await event.insert()
    
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
        from uuid import UUID
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        user = await User.find_one(User.id == user_uuid)
        
        if not user:
            return
            
        user_status = user.lead_status.value if hasattr(user.lead_status, 'value') else user.lead_status
        if user_status == LeadStatusEnum.UNSUBSCRIBED.value:
            return
            
        updated = False
        
        # Update based on event type
        if event_type == EventTypeEnum.CLICKED.value or event_type == "clicked":
            if user_status != LeadStatusEnum.HOT.value:
                user.lead_status = LeadStatusEnum.HOT.value
                updated = True
        
        elif event_type == EventTypeEnum.OPENED.value or event_type == "opened":
            # Only upgrade to warm if not already hot
            if user_status not in [LeadStatusEnum.HOT.value, LeadStatusEnum.WARM.value]:
                user.lead_status = LeadStatusEnum.WARM.value
                updated = True
                
        if updated:
            await user.save()
    
    run_async(_run())
