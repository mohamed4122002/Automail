from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from ..models import EmailSendingQueue, EmailSend, Setting, User
from ..email_providers import get_email_provider

class EmailRateLimitService:
    def __init__(self):
        pass

    async def get_rate_limit_settings(self) -> dict:
        """Get email rate limiting settings from database."""
        setting = await Setting.find_one(Setting.key == "email_rate_limits")
        
        if setting:
            return setting.value
        
        # Default settings
        return {
            "max_per_hour": 50,
            "max_per_day": 300,
            "enabled": True
        }

    async def check_rate_limit(self) -> tuple[bool, str]:
        """
        Check if we can send more emails based on rate limits.
        
        Returns:
            (can_send: bool, reason: str)
        """
        settings = await self.get_rate_limit_settings()
        
        if not settings.get("enabled", True):
            return True, "Rate limiting disabled"
        
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Count emails sent in last hour via EmailSend log
        sent_last_hour = await EmailSend.find(EmailSend.created_at >= hour_ago).count()
        
        # Count emails sent in last day via EmailSend log
        sent_last_day = await EmailSend.find(EmailSend.created_at >= day_ago).count()
        
        max_per_hour = settings.get("max_per_hour", 50)
        max_per_day = settings.get("max_per_day", 300)
        
        if sent_last_hour >= max_per_hour:
            return False, f"Hourly limit reached ({sent_last_hour}/{max_per_hour})"
        
        if sent_last_day >= max_per_day:
            return False, f"Daily limit reached ({sent_last_day}/{max_per_day})"
        
        return True, "OK"

    async def add_to_queue(
        self,
        user_id: UUID,
        subject: str,
        html_body: str,
        workflow_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None,
        priority: int = 5,
        scheduled_for: Optional[datetime] = None
    ) -> EmailSendingQueue:
        """Add an email to the sending queue."""
        
        queue_item = EmailSendingQueue(
            user_id=user_id,
            workflow_id=workflow_id,
            campaign_id=campaign_id,
            subject=subject,
            html_body=html_body,
            priority=priority,
            scheduled_for=scheduled_for or datetime.utcnow(),
            status="queued"
        )
        
        await queue_item.insert()
        return queue_item

    async def get_next_batch(self, batch_size: int = 10) -> list[EmailSendingQueue]:
        """
        Get next batch of emails to send.
        Respects priority and scheduled time.
        """
        now = datetime.utcnow()
        return await EmailSendingQueue.find(
            EmailSendingQueue.status == "queued",
            EmailSendingQueue.scheduled_for <= now
        ).sort("priority", "scheduled_for").limit(batch_size).to_list()

    async def send_queued_email(self, queue_item: EmailSendingQueue) -> bool:
        """
        Send a single queued email.
        
        Returns:
            success: bool
        """
        try:
            # Mark as sending
            queue_item.status = "sending"
            await queue_item.save()
            
            # Get user email
            user = await User.find_one(User.id == queue_item.user_id)
            
            if not user:
                queue_item.status = "failed"
                queue_item.error_message = "User not found"
                await queue_item.save()
                return False
            
            # Get email provider and send
            provider = await get_email_provider(None)
            message_id = await provider.send_email(
                to_email=user.email,
                subject=queue_item.subject,
                html_body=queue_item.html_body
            )
            
            # Mark as sent in queue
            queue_item.status = "sent"
            await queue_item.save()
            
            # Create EmailSend record (historical log)
            email_send = EmailSend(
                user_id=queue_item.user_id,
                workflow_id=queue_item.workflow_id,
                campaign_id=queue_item.campaign_id,
                subject=queue_item.subject,
                html_body=queue_item.html_body,
                status="sent",
                provider_message_id=message_id,
                metadata={'id': str(message_id)}
            )
            await email_send.insert()
            
            return True
            
        except Exception as e:
            queue_item.status = "failed"
            queue_item.error_message = str(e)
            queue_item.retry_count += 1
            await queue_item.save()
            return False

    async def get_queue_stats(self) -> dict:
        """Get statistics about the email queue."""
        
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        hour_ago = now - timedelta(hours=1)
        
        # Queued count
        queued_count = await EmailSendingQueue.find(EmailSendingQueue.status == "queued").count()
        
        # Sent today (from EmailSend log)
        sent_today = await EmailSend.find(EmailSend.created_at >= day_ago).count()
        
        # Sent last hour (from EmailSend log)
        sent_last_hour = await EmailSend.find(EmailSend.created_at >= hour_ago).count()
        
        # Failed count
        failed_count = await EmailSendingQueue.find(EmailSendingQueue.status == "failed").count()
        
        # Get rate limit settings
        settings = await self.get_rate_limit_settings()
        
        return {
            "queued": queued_count,
            "sent_today": sent_today,
            "sent_last_hour": sent_last_hour,
            "failed": failed_count,
            "max_per_hour": settings.get("max_per_hour", 50),
            "max_per_day": settings.get("max_per_day", 300),
            "rate_limit_enabled": settings.get("enabled", True)
        }
