import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Campaign, EmailSend, Event, EventTypeEnum, User, Workflow
from ..schemas.campaigns import CampaignList, CampaignDetail, CampaignStats, Recipient
from uuid import UUID
from datetime import datetime

class CampaignService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_campaigns(self, owner_id: UUID) -> list[CampaignList]:
        """List all campaigns for a specific owner with real statistics."""
        query = (
            sa.select(Campaign)
            .where(Campaign.owner_id == owner_id)
            .options(sa.orm.selectinload(Campaign.workflow))
            .order_by(Campaign.created_at.desc())
        )
        result = await self.db.execute(query)
        campaigns = result.scalars().all()
        
        results = []
        for c in campaigns:
            # Get real stats for each campaign
            stats = await self._calculate_campaign_stats(c.id)
            results.append(CampaignList(
                id=c.id,
                name=c.name,
                owner_id=c.owner_id,
                status="active" if c.is_active else "paused",
                date=c.created_at.strftime("%Y-%m-%d"),
                stats=stats,
                created_at=c.created_at,
                updated_at=c.updated_at
            ))
        return results

    async def get_campaign_detail(self, campaign_id: UUID, owner_id: UUID = None) -> CampaignDetail:
        """Get detailed campaign information with real data."""
        # Get campaign with workflow
        stmt = sa.select(Campaign).where(Campaign.id == campaign_id)
        if owner_id:
            stmt = stmt.where(Campaign.owner_id == owner_id)
        
        q_campaign = await self.db.execute(stmt)
        campaign = q_campaign.scalar_one_or_none()
        
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
            
        # Get associated workflow info
        q_workflow = await self.db.execute(
            sa.select(Workflow).where(Workflow.campaign_id == campaign_id)
        )
        workflow = q_workflow.scalar_one_or_none()
        workflow_data = None
        if workflow:
            workflow_data = {
                "id": str(workflow.id),
                "name": workflow.name,
                "is_active": workflow.is_active
            }
        
        # Calculate stats
        stats = await self._calculate_campaign_stats(campaign_id)
        
        # Get detailed metrics
        overview_stats = await self._get_overview_stats(campaign_id)
        
        # Get recipients with their status
        recipients = await self._get_recipients(campaign_id)
        
        return CampaignDetail(
            id=campaign.id,
            name=campaign.name,
            owner_id=campaign.owner_id, # Added owner_id
            description=campaign.description, # Added description
            is_active=campaign.is_active, # Added is_active
            contact_list_id=campaign.contact_list_id, # Added contact_list_id
            status="active" if campaign.is_active else "paused",
            stats=stats,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            overview_stats=overview_stats,
            recipients=recipients,
            warmup_config=campaign.warmup_config, # Added warmup_config
            workflow=workflow_data # Added workflow
        )

    async def _calculate_campaign_stats(self, campaign_id: UUID) -> CampaignStats:
        """Calculate real statistics for a campaign."""
        
        # Total sent emails
        q_sent = await self.db.execute(
            sa.select(sa.func.count(EmailSend.id))
            .where(
                EmailSend.campaign_id == campaign_id,
                EmailSend.status == "sent"
            )
        )
        total_sent = q_sent.scalar_one() or 0
        
        if total_sent == 0:
            return CampaignStats(sent=0, open_rate="0%", click_rate="0%")
        
        # Unique opens
        q_opens = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.OPENED
            )
        )
        unique_opens = q_opens.scalar_one() or 0
        
        # Unique clicks
        q_clicks = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.CLICKED
            )
        )
        unique_clicks = q_clicks.scalar_one() or 0
        
        # Calculate rates
        open_rate = (unique_opens / total_sent * 100) if total_sent > 0 else 0
        click_rate = (unique_clicks / total_sent * 100) if total_sent > 0 else 0
        
        return CampaignStats(
            sent=total_sent,
            open_rate=f"{open_rate:.1f}%",
            click_rate=f"{click_rate:.1f}%"
        )

    async def _get_overview_stats(self, campaign_id: UUID) -> list[dict]:
        """Get detailed overview statistics."""
        
        # Total sent
        q_sent = await self.db.execute(
            sa.select(sa.func.count(EmailSend.id))
            .where(
                EmailSend.campaign_id == campaign_id,
                EmailSend.status == "sent"
            )
        )
        total_sent = q_sent.scalar_one() or 0
        
        # Delivered (sent - bounced)
        q_bounced = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.email_send_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.BOUNCED
            )
        )
        bounced = q_bounced.scalar_one() or 0
        delivered = total_sent - bounced
        
        # Unique opens
        q_opens = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.OPENED
            )
        )
        unique_opens = q_opens.scalar_one() or 0
        
        # Unique clicks
        q_clicks = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.CLICKED
            )
        )
        unique_clicks = q_clicks.scalar_one() or 0
        
        # Calculate rates
        delivery_rate = (delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (unique_opens / delivered * 100) if delivered > 0 else 0
        click_rate = (unique_clicks / delivered * 100) if delivered > 0 else 0
        
        return [
            {
                "title": "Emails Sent",
                "value": total_sent,
                "description": "100%"
            },
            {
                "title": "Delivered",
                "value": delivered,
                "description": f"{delivery_rate:.1f}% Delivery Rate"
            },
            {
                "title": "Unique Opens",
                "value": unique_opens,
                "description": f"{open_rate:.1f}% Open Rate"
            },
            {
                "title": "Unique Clicks",
                "value": unique_clicks,
                "description": f"{click_rate:.1f}% Click Rate"
            }
        ]

    async def _get_recipients(self, campaign_id: UUID, limit: int = 50) -> list[Recipient]:
        """Get recipients with their latest activity status."""
        
        # Get all email sends for this campaign with user info
        q = await self.db.execute(
            sa.select(EmailSend, User)
            .join(User, EmailSend.user_id == User.id)
            .where(EmailSend.campaign_id == campaign_id)
            .order_by(EmailSend.created_at.desc())
            .limit(limit)
        )
        results = q.all()
        
        recipients = []
        for email_send, user in results:
            # Determine status based on events
            status = "sent"
            last_activity = "No activity"
            
            # Check for events
            q_events = await self.db.execute(
                sa.select(Event)
                .where(Event.email_send_id == email_send.id)
                .order_by(Event.created_at.desc())
            )
            events = list(q_events.scalars().all())
            
            if events:
                latest_event = events[0]
                if latest_event.type == EventTypeEnum.CLICKED:
                    status = "clicked"
                elif latest_event.type == EventTypeEnum.OPENED:
                    status = "opened"
                elif latest_event.type == EventTypeEnum.BOUNCED:
                    status = "bounced"
                
                # Calculate time since last activity
                time_diff = datetime.utcnow() - latest_event.created_at
                if time_diff.days > 0:
                    last_activity = f"{time_diff.days} days ago"
                elif time_diff.seconds // 3600 > 0:
                    last_activity = f"{time_diff.seconds // 3600} hours ago"
                else:
                    last_activity = f"{time_diff.seconds // 60} minutes ago"
            else:
                # No events, check when sent
                time_diff = datetime.utcnow() - email_send.created_at
                if time_diff.days > 0:
                    last_activity = f"Sent {time_diff.days} days ago"
                elif time_diff.seconds // 3600 > 0:
                    last_activity = f"Sent {time_diff.seconds // 3600} hours ago"
                else:
                    last_activity = f"Sent {time_diff.seconds // 60} minutes ago"
            
            recipients.append(Recipient(
                id=str(user.id),
                email=user.email,
                status=status,
                last_activity=last_activity
            ))
        
        return recipients
