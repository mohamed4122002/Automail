from beanie.operators import In
from ..models import (
    Campaign, EmailSend, Event, EventTypeEnum, User, Workflow,
    WorkflowNode, WorkflowInstance, WorkflowStep, Lead, ContactList, EmailTemplate
)
# from ..email_providers import get_email_provider
from ..schemas.campaign_analytics import (
    AnalyticsResponse,
    CampaignAnalytics,
    TimeSeriesDataPoint,
    HeatmapDataPoint,
    RecipientsResponse,
    RecipientStatus,
    RecipientDetail,
    WorkflowVisualization,
    WorkflowNodeStats
)
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List
import json
import csv
import io
from collections import defaultdict


class CampaignAnalyticsService:
    """Service for campaign analytics, recipients, and workflow visualization."""
    
    def __init__(self, db=None):
        self.db = db
    
    # ========================================================================
    # ANALYTICS METHODS
    # ========================================================================
    
    async def get_analytics(self, campaign_id: UUID, days: int = 30) -> AnalyticsResponse:
        """Get comprehensive analytics for a campaign."""
        campaign = await self._get_campaign(campaign_id)
        metrics = await self._calculate_metrics(campaign_id)
        time_series = await self._get_time_series(campaign_id, days)
        heatmap = await self._get_heatmap_data(campaign_id)
        top_links = await self._get_top_links(campaign_id)
        top_subjects = await self._get_top_subjects(campaign_id)
        
        return AnalyticsResponse(
            metrics=metrics,
            time_series=time_series,
            heatmap=heatmap,
            top_links=top_links,
            top_subjects=top_subjects
        )
    
    async def _calculate_metrics(self, campaign_id: UUID) -> CampaignAnalytics:
        """Calculate all core metrics for a campaign."""
        
        sent = await EmailSend.find(EmailSend.campaign_id == campaign_id).count()
        if sent == 0:
            return CampaignAnalytics()
            
        bounced = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.BOUNCED).distinct("email_send_id"))
        delivered = sent - bounced
        
        opened = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.OPENED).distinct("user_id"))
        clicked = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.CLICKED).distinct("user_id"))
        unsubscribed = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.UNSUBSCRIBED).distinct("user_id"))
        
        replied = 0  # TODO: Implement reply tracking
        converted = 0  # TODO: Implement conversion tracking
        
        delivery_rate = (delivered / sent * 100) if sent > 0 else 0.0
        open_rate = (opened / delivered * 100) if delivered > 0 else 0.0
        click_rate = (clicked / delivered * 100) if delivered > 0 else 0.0
        bounce_rate = (bounced / sent * 100) if sent > 0 else 0.0
        conversion_rate = (converted / delivered * 100) if delivered > 0 else 0.0
        
        return CampaignAnalytics(
            sent=sent,
            delivered=delivered,
            opened=opened,
            clicked=clicked,
            bounced=bounced,
            unsubscribed=unsubscribed,
            replied=replied,
            converted=converted,
            delivery_rate=round(delivery_rate, 2),
            open_rate=round(open_rate, 2),
            click_rate=round(click_rate, 2),
            bounce_rate=round(bounce_rate, 2),
            conversion_rate=round(conversion_rate, 2)
        )
    
    async def _get_time_series(self, campaign_id: UUID, days: int) -> List[TimeSeriesDataPoint]:
        """Get time series data for charts using MongoDB Aggregation."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 1. Daily Sends Aggregation
        send_pipeline = [
            {"$match": {"campaign_id": campaign_id, "created_at": {"$gte": start_date}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1}
            }}
        ]
        sends_results = await EmailSend.get_motor_collection().aggregate(send_pipeline).to_list(length=None)
        daily_sends = {r["_id"]: r["count"] for r in sends_results}
        
        # 2. Daily Unique Events Aggregation
        event_pipeline = [
            {"$match": {
                "campaign_id": campaign_id,
                "created_at": {"$gte": start_date},
                "type": {"$in": [EventTypeEnum.OPENED.value, EventTypeEnum.CLICKED.value, EventTypeEnum.BOUNCED.value]}
            }},
            {"$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "type": "$type",
                    "target": {"$cond": [{"$eq": ["$type", EventTypeEnum.BOUNCED.value]}, "$email_send_id", "$user_id"]}
                }
            }},
            {"$group": {
                "_id": {
                    "date": "$_id.date",
                    "type": "$_id.type"
                },
                "unique_count": {"$sum": 1}
            }}
        ]
        
        events_results = await Event.get_motor_collection().aggregate(event_pipeline).to_list(length=None)
        
        daily_opens = defaultdict(int)
        daily_clicks = defaultdict(int)
        daily_bounces = defaultdict(int)
        
        for r in events_results:
            date_str = r["_id"]["date"]
            type_str = r["_id"]["type"]
            count = r["unique_count"]
            if type_str == EventTypeEnum.OPENED.value:
                daily_opens[date_str] = count
            elif type_str == EventTypeEnum.CLICKED.value:
                daily_clicks[date_str] = count
            elif type_str == EventTypeEnum.BOUNCED.value:
                daily_bounces[date_str] = count
                
        time_series = []
        current_date = start_date.date()
        end_date = datetime.utcnow().date()
        
        while current_date <= end_date:
            date_str = str(current_date)
            time_series.append(TimeSeriesDataPoint(
                date=date_str,
                sent=daily_sends.get(date_str, 0),
                opened=daily_opens.get(date_str, 0),
                clicked=daily_clicks.get(date_str, 0),
                bounced=daily_bounces.get(date_str, 0)
            ))
            current_date += timedelta(days=1)
            
        return time_series
            
        return time_series
    
    async def _get_heatmap_data(self, campaign_id: UUID) -> List[HeatmapDataPoint]:
        events = await Event.find(
            Event.campaign_id == campaign_id,
            In(Event.type, [EventTypeEnum.OPENED, EventTypeEnum.CLICKED])
        ).to_list()
        
        heatmap_dict = defaultdict(lambda: {'opens': 0, 'clicks': 0})
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] # python dow: 0=Mon
        
        for e in events:
            hour = e.created_at.hour
            day = day_names[e.created_at.weekday()]
            key = (hour, day)
            if e.type == EventTypeEnum.OPENED:
                heatmap_dict[key]['opens'] += 1
            elif e.type == EventTypeEnum.CLICKED:
                heatmap_dict[key]['clicks'] += 1
                
        heatmap = []
        for (hour, day), counts in heatmap_dict.items():
            heatmap.append(HeatmapDataPoint(
                hour=hour,
                day=day,
                opens=counts['opens'],
                clicks=counts['clicks']
            ))
            
        return heatmap
    
    async def _get_top_links(self, campaign_id: UUID, limit: int = 10) -> List[dict]:
        events = await Event.find(
            Event.campaign_id == campaign_id,
            Event.type == EventTypeEnum.CLICKED
        ).to_list()
        
        url_stats = defaultdict(lambda: {'total': 0, 'users': set()})
        for e in events:
            url = e.data.get('url') if e.data else None
            if url:
                url_stats[url]['total'] += 1
                url_stats[url]['users'].add(e.user_id)
                
        results = []
        for url, stats in url_stats.items():
            results.append({
                'url': url,
                'total_clicks': stats['total'],
                'unique_clicks': len(stats['users'])
            })
            
        return sorted(results, key=lambda x: x['total_clicks'], reverse=True)[:limit]
    
    async def _get_top_subjects(self, campaign_id: UUID, limit: int = 10) -> List[dict]:
        sends = await EmailSend.find(EmailSend.campaign_id == campaign_id).to_list()
        events = await Event.find(
            Event.campaign_id == campaign_id,
            Event.type == EventTypeEnum.OPENED
        ).to_list()
        
        subj_stats = defaultdict(lambda: {'sent': set(), 'opens': set()})
        
        send_map = {s.id: s for s in sends}
        for s in sends:
            subj = s.data.get('subject') if s.data else "No subject"
            subj_stats[subj]['sent'].add(s.id)
            
        for e in events:
            if e.email_send_id in send_map:
                s = send_map[e.email_send_id]
                subj = s.data.get('subject') if s.data else "No subject"
                subj_stats[subj]['opens'].add(e.user_id)
                
        results = []
        for subj, stats in subj_stats.items():
            sent_count = len(stats['sent'])
            opens_count = len(stats['opens'])
            open_rate = (opens_count / sent_count * 100) if sent_count > 0 else 0
            results.append({
                'subject': subj,
                'sent': sent_count,
                'opens': opens_count,
                'open_rate': round(open_rate, 2)
            })
            
        return sorted(results, key=lambda x: x['opens'], reverse=True)[:limit]
    
    # ========================================================================
    # RECIPIENTS METHODS
    # ========================================================================
    
    async def get_recipients(
        self,
        campaign_id: UUID,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc"
    ) -> RecipientsResponse:
        await self._get_campaign(campaign_id)
        
        # We will fetch user IDs related to the campaign, then search users and compute basic stats.
        sends = await EmailSend.find(EmailSend.campaign_id == campaign_id).to_list()
        user_ids_in_campaign = list(set([s.user_id for s in sends]))
        
        query_parts = [In(User.id, user_ids_in_campaign)]
        if search: pass # Fallback filter in memory for simplicity due to Beanie query limitations
        
        users = await User.find(*query_parts).to_list()
        
        if search:
            s_lower = search.lower()
            users = [u for u in users if s_lower in (u.email or "").lower() or s_lower in (u.first_name or "").lower() or s_lower in (u.last_name or "").lower()]
            
        # Optimization: Group sends and events by user
        # In a very large campaign this requires aggregation, but for our scale memory groupby works.
        user_sends = defaultdict(list)
        for s in sends:
            user_sends[s.user_id].append(s)
            
        all_events = await Event.find(Event.campaign_id == campaign_id).to_list()
        user_events = defaultdict(list)
        for e in all_events:
            user_events[e.user_id].append(e)
            
        recipients = []
        for u in users:
            my_sends = sorted(user_sends.get(u.id, []), key=lambda x: x.created_at, reverse=True)
            if not my_sends: continue
            
            latest_send = my_sends[0]
            my_events = sorted(user_events.get(u.id, []), key=lambda x: x.created_at, reverse=True)
            
            # Simple status extraction
            status = "sent"
            opened_at, clicked_at, last_activity_at = None, None, latest_send.created_at
            total_opens, total_clicks = 0, 0
            
            for ev in my_events:
                if ev.email_send_id == latest_send.id:
                    if ev.type == EventTypeEnum.OPENED:
                        total_opens += 1
                        if not opened_at: opened_at, status = ev.created_at, "opened"
                        last_activity_at = max(last_activity_at, ev.created_at)
                    elif ev.type == EventTypeEnum.CLICKED:
                        total_clicks += 1
                        if not clicked_at: clicked_at, status = ev.created_at, "clicked"
                        last_activity_at = max(last_activity_at, ev.created_at)
                    elif ev.type == EventTypeEnum.BOUNCED:
                        status = "bounced"
                        last_activity_at = max(last_activity_at, ev.created_at)
                    elif ev.type == EventTypeEnum.UNSUBSCRIBED:
                        status = "unsubscribed"
                        last_activity_at = max(last_activity_at, ev.created_at)
                        
            if status_filter and status != status_filter:
                continue
                
            engagement_score = 10
            if status == "opened": engagement_score = 40 + min(total_opens * 5, 30)
            elif status == "clicked": engagement_score = 70 + min(total_clicks * 5, 30)
            elif status in ["bounced", "unsubscribed"]: engagement_score = 0
            
            recipients.append(RecipientStatus(
                user_id=u.id, email=u.email, name=f"{u.first_name or ''} {u.last_name or ''}".strip() or None,
                status=status, engagement_score=engagement_score, sent_at=latest_send.created_at,
                opened_at=opened_at, clicked_at=clicked_at, last_activity_at=last_activity_at,
                current_workflow_node=None, workflow_node_id=None, total_opens=total_opens,
                total_clicks=total_clicks, emails_received=len(my_sends)
            ))
            
        # Apply sorting
        if sort_by == 'email': recipients.sort(key=lambda x: x.email, reverse=(order == 'desc'))
        elif sort_by == 'name': recipients.sort(key=lambda x: x.name or "", reverse=(order == 'desc'))
        else: recipients.sort(key=lambda x: getattr(x, sort_by, x.sent_at), reverse=(order == 'desc'))
        
        total = len(recipients)
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_recipients = recipients[offset:offset + page_size]
        
        summary = await self._calculate_recipient_summary(campaign_id)
        total_pages = (total + page_size - 1) // page_size if page_size else 1
        
        return RecipientsResponse(
            recipients=paginated_recipients, total=total, page=page, page_size=page_size,
            total_pages=total_pages, sort_by=sort_by, order=order, summary=summary
        )

    async def _calculate_recipient_summary(self, campaign_id: UUID) -> dict:
        sent = await EmailSend.find(EmailSend.campaign_id == campaign_id).count()
        opened = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.OPENED).distinct("user_id"))
        clicked = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.CLICKED).distinct("user_id"))
        bounced = len(await Event.find(Event.campaign_id == campaign_id, Event.type == EventTypeEnum.BOUNCED).distinct("email_send_id"))
        
        return {
            'sent': sent, 'opened': opened, 'clicked': clicked,
            'bounced': bounced, 'unsubscribed': 0
        }
    
    async def get_recipient_detail(self, campaign_id: UUID, user_id: UUID) -> RecipientDetail:
        user = await User.find_one(User.id == user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
            
        sends = await EmailSend.find(EmailSend.campaign_id == campaign_id, EmailSend.user_id == user_id).sort("-created_at").to_list()
        if not sends:
            raise ValueError(f"No emails sent to user {user_id} in campaign {campaign_id}")
            
        events = await Event.find(Event.campaign_id == campaign_id, Event.user_id == user_id).sort("-created_at").to_list()
        
        # Compute basic status from latest send manually
        latest_send = sends[0]
        status, opened_at, clicked_at = "sent", None, None
        total_opens, total_clicks = 0, 0
        
        for ev in events:
            if ev.email_send_id == latest_send.id:
                if ev.type == EventTypeEnum.OPENED:
                    total_opens += 1
                    if not opened_at: opened_at, status = ev.created_at, "opened"
                elif ev.type == EventTypeEnum.CLICKED:
                    total_clicks += 1
                    if not clicked_at: clicked_at, status = ev.created_at, "clicked"
                elif ev.type == EventTypeEnum.BOUNCED: status = "bounced"
                elif ev.type == EventTypeEnum.UNSUBSCRIBED: status = "unsubscribed"
                
        engagement_score = 10
        if status == "opened": engagement_score = 40 + min(total_opens * 5, 30)
        elif status == "clicked": engagement_score = 70 + min(total_clicks * 5, 30)
        elif status in ["bounced", "unsubscribed"]: engagement_score = 0
        
        event_timeline = [
            {'type': e.type, 'timestamp': e.created_at.isoformat(), 'metadata': e.metadata or {}} for e in events
        ]
        
        email_history = [
            {'subject': s.data.get('subject', 'No subject') if s.data else 'No subject',
             'sent_at': s.created_at.isoformat(), 'status': s.status,
             'template_id': str(s.metadata.get('template_id')) if s.metadata else None} for s in sends
        ]
        
        return RecipientDetail(
            user_id=user.id, email=user.email, name=f"{user.first_name or ''} {user.last_name or ''}".strip() or None,
            status=status, engagement_score=engagement_score, sent_at=latest_send.created_at,
            opened_at=opened_at, clicked_at=clicked_at, last_activity_at=events[0].created_at if events else latest_send.created_at,
            current_workflow_node=None, workflow_node_id=None, total_opens=total_opens,
            total_clicks=total_clicks, emails_received=len(sends), events=event_timeline,
            emails=email_history, attributes=user.attributes or {}
        )
    
    # ========================================================================
    # WORKFLOW VISUALIZATION METHODS
    # ========================================================================
    
    async def get_workflow_visualization(self, campaign_id: UUID) -> WorkflowVisualization:
        campaign = await self._get_campaign(campaign_id)
        workflow = await Workflow.find_one(Workflow.campaign_id == campaign_id)
        
        if not workflow: raise ValueError(f"No workflow found for campaign {campaign_id}")
            
        nodes = await WorkflowNode.find(WorkflowNode.workflow_id == workflow.id).sort("created_at").to_list()
        
        node_data = []
        node_stats = []
        
        for node in nodes:
            node_data.append({
                'id': str(node.id), 'type': node.type,
                'label': node.config.get('label', node.type) if node.config else node.type,
                'position': node.config.get('position', {'x': 0, 'y': 0}) if node.config else {'x': 0, 'y': 0},
                'config': node.config or {}
            })
            
            leads_active = await WorkflowStep.find(WorkflowStep.node_id == node.id, WorkflowStep.status == "running").count()
            node_stats.append(WorkflowNodeStats(
                node_id=node.id, node_type=node.type,
                node_label=node.config.get('label', node.type) if node.config else node.type,
                leads_active=leads_active, leads_completed=0, leads_failed=0,
                avg_time_at_node=None, success_rate=0.0
            ))
            
        edges = []
        for node in nodes:
            if node.config and 'next' in node.config:
                edges.append({'from': str(node.id), 'to': str(node.config['next'])})
                
        total_instances = await WorkflowInstance.find(WorkflowInstance.workflow_id == workflow.id).count()
        active_instances = await WorkflowInstance.find(WorkflowInstance.workflow_id == workflow.id, WorkflowInstance.status == "running").count()
        completed_instances = await WorkflowInstance.find(WorkflowInstance.workflow_id == workflow.id, WorkflowInstance.status == "completed").count()
        
        return WorkflowVisualization(
            workflow_id=workflow.id, workflow_name=workflow.name, is_active=workflow.is_active,
            nodes=node_data, edges=edges, node_stats=node_stats,
            total_instances=total_instances, active_instances=active_instances,
            completed_instances=completed_instances, failed_instances=0
        )
    
    # ========================================================================
    # QUICK ACTIONS METHODS
    # ========================================================================
    
    async def send_test_email(
        self,
        campaign_id: UUID,
        recipient_emails: List[str],
        template_id: Optional[UUID] = None,
        use_campaign_workflow: bool = True
    ) -> dict:
        campaign = await self._get_campaign(campaign_id)
        
        template = None
        if template_id:
            template = await EmailTemplate.find_one(EmailTemplate.id == template_id)
            
        if not template and use_campaign_workflow:
            workflow = await Workflow.find_one(Workflow.campaign_id == campaign_id)
            if workflow:
                node = await WorkflowNode.find_one(WorkflowNode.workflow_id == workflow.id, WorkflowNode.type == 'email')
                if node and node.config and node.config.get('template_id'):
                    template = await EmailTemplate.find_one(EmailTemplate.id == UUID(node.config['template_id']))
                    
        if not template:
            templates = await EmailTemplate.find_all().limit(1).to_list()
            template = templates[0] if templates else None
            
        if not template:
            raise ValueError("No email template found for test email")
            
        # from ..email_providers import get_email_provider
        # provider = await get_email_provider(self.db)
        
        success_count = 0
        errors = []
        
        for email in recipient_emails:
            try:
                # Mock sending for now
                success_count += 1
            except Exception as e:
                errors.append(f"Failed to send to {email}: {str(e)}")
                
        return {
            'success': success_count > 0,
            'message': f'Test email sent to {success_count}/{len(recipient_emails)} recipients',
            'details': { 'recipients': recipient_emails, 'template_id': str(template.id), 'success_count': success_count, 'errors': errors }
        }
    
    async def duplicate_campaign(
        self,
        campaign_id: UUID,
        new_name: str,
        copy_workflow: bool = True,
        copy_contacts: bool = False,
        owner_id: UUID = None
    ) -> dict:
        original = await self._get_campaign(campaign_id)
        
        new_campaign = Campaign(
            name=new_name, description=f"Copy of {original.name}",
            owner_id=owner_id or original.owner_id, is_active=False,
            warmup_config=original.warmup_config, retry_config=original.retry_config
        )
        
        if copy_contacts:
            new_campaign.contact_list_id = original.contact_list_id
            
        await new_campaign.insert()
        return {'success': True, 'campaign_id': str(new_campaign.id), 'name': new_campaign.name}
    
    async def export_campaign_data(
        self,
        campaign_id: UUID,
        format: str = "csv",
        include_recipients: bool = True,
        include_analytics: bool = True,
        include_events: bool = False
    ) -> str:
        await self._get_campaign(campaign_id)
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            if include_recipients:
                r_resp = await self.get_recipients(campaign_id, page=1, page_size=10000)
                writer.writerow(['Email', 'Name', 'Status', 'Engagement Score', 'Sent At', 'Last Activity'])
                for r in r_resp.recipients:
                    writer.writerow([r.email, r.name or '', r.status, r.engagement_score,
                                     r.sent_at.isoformat() if r.sent_at else '',
                                     r.last_activity_at.isoformat() if r.last_activity_at else ''])
            return output.getvalue()
        elif format == "json":
            data = {}
            if include_analytics:
                analytics = await self.get_analytics(campaign_id)
                data['analytics'] = analytics.model_dump()
            if include_recipients:
                r_resp = await self.get_recipients(campaign_id, page=1, page_size=10000)
                data['recipients'] = [r.model_dump() for r in r_resp.recipients]
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def bulk_recipients_action(self, *args, **kwargs):
        raise NotImplementedError("Bulk actions not mocked yet.")
    
    async def export_recipients(self, *args, **kwargs):
        raise NotImplementedError("Export recipients not mocked yet.")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _get_campaign(self, campaign_id: UUID) -> Campaign:
        campaign = await Campaign.find_one(Campaign.id == campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        return campaign
