import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from ..models import EmailSendingQueue, EmailSend, Setting
from ..email_providers import get_email_provider


class EmailRateLimitService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_rate_limit_settings(self) -> dict:
        """Get email rate limiting settings from database."""
        query = sa.select(Setting).where(Setting.key == "email_rate_limits")
        result = await self.db.execute(query)
        setting = result.scalar_one_or_none()
        
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
        hour_query = sa.select(sa.func.count(EmailSend.id)).where(
            EmailSend.created_at >= hour_ago
        )
        hour_result = await self.db.execute(hour_query)
        sent_last_hour = hour_result.scalar_one() or 0
        
        # Count emails sent in last day via EmailSend log
        day_query = sa.select(sa.func.count(EmailSend.id)).where(
            EmailSend.created_at >= day_ago
        )
        day_result = await self.db.execute(day_query)
        sent_last_day = day_result.scalar_one() or 0
        
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
        
        self.db.add(queue_item)
        await self.db.commit()
        await self.db.refresh(queue_item)
        
        return queue_item

    async def get_next_batch(self, batch_size: int = 10) -> list[EmailSendingQueue]:
        """
        Get next batch of emails to send.
        Respects priority and scheduled time.
        """
        now = datetime.utcnow()
        
        query = sa.select(EmailSendingQueue).where(
            sa.and_(
                EmailSendingQueue.status == "queued",
                EmailSendingQueue.scheduled_for <= now
            )
        ).order_by(
            EmailSendingQueue.priority.asc(),
            EmailSendingQueue.scheduled_for.asc()
        ).limit(batch_size)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def send_queued_email(self, queue_item: EmailSendingQueue) -> bool:
        """
        Send a single queued email.
        
        Returns:
            success: bool
        """
        try:
            # Mark as sending
            queue_item.status = "sending"
            await self.db.commit()
            
            # Get user email
            from ..models import User
            user_query = sa.select(User).where(User.id == queue_item.user_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                queue_item.status = "failed"
                queue_item.error_message = "User not found"
                await self.db.commit()
                return False
            
            # Get email provider and send
            provider = await get_email_provider(self.db)
            message_id = await provider.send_email(
                to_email=user.email,
                subject=queue_item.subject,
                html_body=queue_item.html_body
            )
            
            # Mark as sent in queue (no sent_at attribute exists)
            queue_item.status = "sent"
            await self.db.commit()
            
            # Create EmailSend record (historical log)
            email_send = EmailSend(
                user_id=queue_item.user_id,
                workflow_id=queue_item.workflow_id,
                campaign_id=queue_item.campaign_id,
                subject=queue_item.subject,
                html_body=queue_item.html_body,
                status="sent",
                provider_message_id=message_id
            )
            self.db.add(email_send)
            await self.db.commit()
            
            return True
            
        except Exception as e:
            queue_item.status = "failed"
            queue_item.error_message = str(e)
            queue_item.retry_count += 1
            await self.db.commit()
            return False

    async def get_queue_stats(self) -> dict:
        """Get statistics about the email queue."""
        
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        hour_ago = now - timedelta(hours=1)
        
        # Queued count
        queued_query = sa.select(sa.func.count(EmailSendingQueue.id)).where(
            EmailSendingQueue.status == "queued"
        )
        queued_result = await self.db.execute(queued_query)
        queued_count = queued_result.scalar_one() or 0
        
        # Sent today (from EmailSend log)
        sent_today_query = sa.select(sa.func.count(EmailSend.id)).where(
            EmailSend.created_at >= day_ago
        )
        sent_today_result = await self.db.execute(sent_today_query)
        sent_today = sent_today_result.scalar_one() or 0
        
        # Sent last hour (from EmailSend log)
        sent_hour_query = sa.select(sa.func.count(EmailSend.id)).where(
            EmailSend.created_at >= hour_ago
        )
        sent_hour_result = await self.db.execute(sent_hour_query)
        sent_last_hour = sent_hour_result.scalar_one() or 0
        
        # Failed count
        failed_query = sa.select(sa.func.count(EmailSendingQueue.id)).where(
            EmailSendingQueue.status == "failed"
        )
        failed_result = await self.db.execute(failed_query)
        failed_count = failed_result.scalar_one() or 0
        
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
