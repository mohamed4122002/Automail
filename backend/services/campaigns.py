from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from ..models import Campaign, EmailSend, Event, EventTypeEnum, User, Workflow
from ..schemas.campaigns import CampaignList, CampaignDetail, CampaignStats, Recipient
from pydantic import Field, BaseModel

class CampaignProjection(BaseModel):
    id: UUID = Field(alias="_id")
    name: str
    owner_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

class EmailSendProjection(BaseModel):
    id: UUID = Field(alias="_id")
    user_id: UUID
    created_at: datetime

class UserProjection(BaseModel):
    id: UUID = Field(alias="_id")
    email: str

class CampaignService:
    def __init__(self):
        pass

    async def list_campaigns(self, owner_id: UUID) -> list[CampaignList]:
        campaigns = await Campaign.find(Campaign.owner_id == owner_id)\
            .project(CampaignProjection)\
            .sort("-created_at").to_list()
        
        results = []
        for c in campaigns:
            c_id = c.id
            stats = await self._calculate_campaign_stats(c_id)
            results.append(CampaignList(
                id=c_id,
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
        if owner_id:
            campaign = await Campaign.find_one(Campaign.id == campaign_id, Campaign.owner_id == owner_id)
        else:
            campaign = await Campaign.find_one(Campaign.id == campaign_id)
            
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
            
        workflow = await Workflow.find_one(Workflow.campaign_id == campaign_id)
        workflow_data = None
        if workflow:
            workflow_data = {
                "id": str(workflow.id),
                "name": workflow.name,
                "is_active": workflow.is_active
            }
        
        stats = await self._calculate_campaign_stats(campaign_id)
        overview_stats = await self._get_overview_stats(campaign_id)
        recipients = await self._get_recipients(campaign_id)
        
        return CampaignDetail(
            id=campaign.id,
            name=campaign.name,
            owner_id=campaign.owner_id,
            description=campaign.description,
            is_active=campaign.is_active,
            contact_list_id=campaign.contact_list_id,
            status="active" if campaign.is_active else "paused",
            stats=stats,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            overview_stats=overview_stats,
            recipients=recipients,
            warmup_config=campaign.warmup_config,
            workflow=workflow_data
        )

    async def _calculate_campaign_stats(self, campaign_id: UUID) -> CampaignStats:
        total_sent = await EmailSend.find(EmailSend.campaign_id == campaign_id, EmailSend.status == "sent").count()
        
        if total_sent == 0:
            return CampaignStats(sent=0, open_rate="0%", click_rate="0%")
        
        unique_opens = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.OPENED).distinct("user_id"))
        unique_clicks = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.CLICKED).distinct("user_id"))
        
        open_rate = (unique_opens / total_sent * 100) if total_sent > 0 else 0
        click_rate = (unique_clicks / total_sent * 100) if total_sent > 0 else 0
        
        return CampaignStats(
            sent=total_sent,
            open_rate=f"{open_rate:.1f}%",
            click_rate=f"{click_rate:.1f}%"
        )

    async def _get_overview_stats(self, campaign_id: UUID) -> list[dict]:
        total_sent = await EmailSend.find(EmailSend.campaign_id == campaign_id, EmailSend.status == "sent").count()
        bounced = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.BOUNCED).distinct("email_send_id"))
        delivered = total_sent - bounced
        
        unique_opens = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.OPENED).distinct("user_id"))
        unique_clicks = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.CLICKED).distinct("user_id"))
        
        delivery_rate = (delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (unique_opens / delivered * 100) if delivered > 0 else 0
        click_rate = (unique_clicks / delivered * 100) if delivered > 0 else 0
        
        return [
            {"title": "Emails Sent", "value": total_sent, "description": "100%"},
            {"title": "Delivered", "value": delivered, "description": f"{delivery_rate:.1f}% Delivery Rate"},
            {"title": "Unique Opens", "value": unique_opens, "description": f"{open_rate:.1f}% Open Rate"},
            {"title": "Unique Clicks", "value": unique_clicks, "description": f"{click_rate:.1f}% Click Rate"}
        ]

    async def _get_recipients(self, campaign_id: UUID, limit: int = 50) -> list[Recipient]:
        email_sends = await EmailSend.find(EmailSend.campaign_id == campaign_id)\
            .project(EmailSendProjection)\
            .sort("-created_at").limit(limit).to_list()
        
        # Optimize by fetching all users at once
        user_ids = [send.user_id for send in email_sends if send.user_id]
        users = await User.find({"_id": {"$in": user_ids}})\
            .project(UserProjection)\
            .to_list()
        user_map = {u.id: u for u in users}
        
        recipients = []
        for send in email_sends:
            user = user_map.get(send.user_id)
            if not user: continue
            
            send_id = send.id
            events = await Event.find(Event.email_send_id == send_id).sort("-created_at").to_list()
            
            status = "sent"
            last_activity = "No activity"
            
            if events:
                latest_event = events[0]
                if latest_event.type == EventTypeEnum.CLICKED: status = "clicked"
                elif latest_event.type == EventTypeEnum.OPENED: status = "opened"
                elif latest_event.type == EventTypeEnum.BOUNCED: status = "bounced"
                
                time_diff = datetime.utcnow() - latest_event.created_at
                last_activity = self._format_time_diff(time_diff)
            else:
                time_diff = datetime.utcnow() - send.created_at
                last_activity = "Sent " + self._format_time_diff(time_diff)
                
            recipients.append(Recipient(
                id=str(user.id),
                email=user.email,
                status=status,
                last_activity=last_activity
            ))
            
        return recipients

    def _format_time_diff(self, td) -> str:
        if td.days > 0: return f"{td.days} days ago"
        if td.seconds // 3600 > 0: return f"{td.seconds // 3600} hours ago"
        return f"{td.seconds // 60} minutes ago"
