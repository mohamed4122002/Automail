import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import (
    Campaign, EmailSend, Event, EventTypeEnum, User, Workflow,
    WorkflowNode, WorkflowInstance, WorkflowStep, Lead, ContactList, EmailTemplate
)
from ..email_providers import get_email_provider
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
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========================================================================
    # ANALYTICS METHODS
    # ========================================================================
    
    async def get_analytics(self, campaign_id: UUID, days: int = 30) -> AnalyticsResponse:
        """Get comprehensive analytics for a campaign."""
        
        # Verify campaign exists
        campaign = await self._get_campaign(campaign_id)
        
        # Get core metrics
        metrics = await self._calculate_metrics(campaign_id)
        
        # Get time series data
        time_series = await self._get_time_series(campaign_id, days)
        
        # Get heatmap data
        heatmap = await self._get_heatmap_data(campaign_id)
        
        # Get top performing links and subjects
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
        
        # Total sent
        q_sent = await self.db.execute(
            sa.select(sa.func.count(EmailSend.id))
            .where(EmailSend.campaign_id == campaign_id)
        )
        sent = q_sent.scalar_one() or 0
        
        if sent == 0:
            return CampaignAnalytics()
        
        # Bounced emails
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
        delivered = sent - bounced
        
        # Unique opens
        q_opened = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.OPENED
            )
        )
        opened = q_opened.scalar_one() or 0
        
        # Unique clicks
        q_clicked = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.CLICKED
            )
        )
        clicked = q_clicked.scalar_one() or 0
        
        # Unsubscribed
        q_unsubscribed = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.UNSUBSCRIBED
            )
        )
        unsubscribed = q_unsubscribed.scalar_one() or 0
        
        # Replied (if tracked)
        replied = 0  # TODO: Implement reply tracking
        
        # Converted (if tracked)
        converted = 0  # TODO: Implement conversion tracking
        
        # Calculate rates
        delivery_rate = (delivered / sent * 100) if sent > 0 else 0.0
        open_rate = (opened / delivered * 100) if delivered > 0 else 0.0
        click_rate = (clicked / delivered * 100) if delivered > 0 else 0.0
        bounce_rate = (bounced / sent * 100) if sent > 0 else 0.0
        conversion_rate = (converted / delivered * 100) if delivered > 0 else 0.0
        
        # Calculate trends (compare to previous period)
        # TODO: Implement trend calculation
        
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
        """Get time series data for charts."""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get daily email sends
        q_daily = await self.db.execute(
            sa.select(
                sa.func.date(EmailSend.created_at).label('date'),
                sa.func.count(EmailSend.id).label('sent')
            )
            .where(
                EmailSend.campaign_id == campaign_id,
                EmailSend.created_at >= start_date
            )
            .group_by(sa.func.date(EmailSend.created_at))
            .order_by(sa.func.date(EmailSend.created_at))
        )
        daily_sends = {str(row.date): row.sent for row in q_daily.all()}
        
        # Get daily opens
        q_opens = await self.db.execute(
            sa.select(
                sa.func.date(Event.created_at).label('date'),
                sa.func.count(sa.func.distinct(Event.user_id)).label('opens')
            )
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.OPENED,
                Event.created_at >= start_date
            )
            .group_by(sa.func.date(Event.created_at))
        )
        daily_opens = {str(row.date): row.opens for row in q_opens.all()}
        
        # Get daily clicks
        q_clicks = await self.db.execute(
            sa.select(
                sa.func.date(Event.created_at).label('date'),
                sa.func.count(sa.func.distinct(Event.user_id)).label('clicks')
            )
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.CLICKED,
                Event.created_at >= start_date
            )
            .group_by(sa.func.date(Event.created_at))
        )
        daily_clicks = {str(row.date): row.clicks for row in q_clicks.all()}
        
        # Get daily bounces
        q_bounces = await self.db.execute(
            sa.select(
                sa.func.date(Event.created_at).label('date'),
                sa.func.count(sa.func.distinct(Event.email_send_id)).label('bounces')
            )
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.BOUNCED,
                Event.created_at >= start_date
            )
            .group_by(sa.func.date(Event.created_at))
        )
        daily_bounces = {str(row.date): row.bounces for row in q_bounces.all()}
        
        # Build time series
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
    
    async def _get_heatmap_data(self, campaign_id: UUID) -> List[HeatmapDataPoint]:
        """Get engagement heatmap data (hour of day x day of week)."""
        
        # Get opens by hour and day
        q_heatmap = await self.db.execute(
            sa.select(
                sa.func.extract('hour', Event.created_at).label('hour'),
                sa.func.extract('dow', Event.created_at).label('dow'),  # 0=Sunday
                sa.func.count(Event.id).label('count'),
                Event.type
            )
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                sa.or_(Event.type == EventTypeEnum.OPENED, Event.type == EventTypeEnum.CLICKED)
            )
            .group_by(
                sa.func.extract('hour', Event.created_at),
                sa.func.extract('dow', Event.created_at),
                Event.type
            )
        )
        
        # Organize data
        heatmap_dict = defaultdict(lambda: {'opens': 0, 'clicks': 0})
        day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        
        for row in q_heatmap.all():
            hour = int(row.hour)
            day = day_names[int(row.dow)]
            key = (hour, day)
            
            if row.type == EventTypeEnum.OPENED:
                heatmap_dict[key]['opens'] += row.count
            elif row.type == EventTypeEnum.CLICKED:
                heatmap_dict[key]['clicks'] += row.count
        
        # Convert to list
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
        """Get top performing links."""
        
        q_links = await self.db.execute(
            sa.select(
                Event.data['url'].astext.label('url'),
                sa.func.count(Event.id).label('total_clicks'),
                sa.func.count(sa.func.distinct(Event.user_id)).label('unique_clicks')
            )
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.CLICKED,
                Event.data['url'].astext.isnot(None)
            )
            .group_by(sa.text('url'))
            .order_by(sa.text('total_clicks DESC'))
            .limit(limit)
        )
        
        return [
            {
                'url': row.url,
                'total_clicks': row.total_clicks,
                'unique_clicks': row.unique_clicks
            }
            for row in q_links.all()
        ]
    
    async def _get_top_subjects(self, campaign_id: UUID, limit: int = 10) -> List[dict]:
        """Get top performing email subjects."""
        
        q_subjects = await self.db.execute(
            sa.select(
                EmailSend.data['subject'].astext.label('subject'),
                sa.func.count(sa.func.distinct(EmailSend.id)).label('sent'),
                sa.func.count(sa.func.distinct(Event.user_id)).label('opens')
            )
            .select_from(EmailSend)
            .outerjoin(
                Event,
                sa.and_(
                    Event.email_send_id == EmailSend.id,
                    Event.type == EventTypeEnum.OPENED
                )
            )
            .where(
                EmailSend.campaign_id == campaign_id,
                EmailSend.data['subject'].astext.isnot(None)
            )
            .group_by(sa.text('subject'))
            .order_by(sa.text('opens DESC'))
            .limit(limit)
        )
        
        results = []
        for row in q_subjects.all():
            open_rate = (row.opens / row.sent * 100) if row.sent > 0 else 0
            results.append({
                'subject': row.subject,
                'sent': row.sent,
                'opens': row.opens,
                'open_rate': round(open_rate, 2)
            })
        
        return results
    
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
        """Get paginated list of campaign recipients."""
        
        # Verify campaign exists
        await self._get_campaign(campaign_id)
        
        # Build base query
        query = (
            sa.select(EmailSend, User)
            .join(User, EmailSend.user_id == User.id)
            .where(EmailSend.campaign_id == campaign_id)
        )
        
        # Apply status filter
        if status_filter:
            query = query.where(EmailSend.status == status_filter)
        
        # Apply search filter
        if search:
            query = query.where(
                sa.or_(
                    User.email.ilike(f'%{search}%'),
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%')
                )
            )
        
        # Get total count
        count_query = sa.select(sa.func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Apply sorting
        if sort_by == 'email':
            sort_col = User.email
        elif sort_by == 'name':
            sort_col = User.last_name  # Sort by last name primarily
        elif sort_by == 'sent_at' or sort_by == 'created_at':
            sort_col = EmailSend.created_at
        else:
            sort_col = EmailSend.created_at
            
        if order == 'asc':
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())
            
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.limit(page_size).offset(offset)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Build recipients list
        recipients = []
        for email_send, user in rows:
            recipient = await self._build_recipient_status(email_send, user, campaign_id)
            
            # Apply status filter
            # Note: status filtering is done in memory because status is derived from events
            # For large datasets, this should be optimized to use subqueries or denormalized status
            if status_filter and recipient.status != status_filter:
                continue
            
            recipients.append(recipient)
        
        # Calculate summary stats
        summary = await self._calculate_recipient_summary(campaign_id)
        
        total_pages = (total + page_size - 1) // page_size
        
        return RecipientsResponse(
            recipients=recipients,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            sort_by=sort_by,
            order=order,
            summary=summary
        )
    
    async def _build_recipient_status(
        self,
        email_send: EmailSend,
        user: User,
        campaign_id: UUID
    ) -> RecipientStatus:
        """Build recipient status from email send and events."""
        
        # Get latest event for this email send
        q_events = await self.db.execute(
            sa.select(Event)
            .where(Event.email_send_id == email_send.id)
            .order_by(Event.created_at.desc())
        )
        events = list(q_events.scalars().all())
        
        # Determine status
        status = "sent"
        opened_at = None
        clicked_at = None
        last_activity_at = email_send.created_at
        
        total_opens = 0
        total_clicks = 0
        
        for event in events:
            if event.type == EventTypeEnum.OPENED:
                total_opens += 1
                if not opened_at:
                    opened_at = event.created_at
                    status = "opened"
                last_activity_at = event.created_at
            elif event.type == EventTypeEnum.CLICKED:
                total_clicks += 1
                if not clicked_at:
                    clicked_at = event.created_at
                    status = "clicked"
                last_activity_at = event.created_at
            elif event.type == EventTypeEnum.BOUNCED:
                status = "bounced"
                last_activity_at = event.created_at
            elif event.type == EventTypeEnum.UNSUBSCRIBED:
                status = "unsubscribed"
                last_activity_at = event.created_at
        
        # Calculate engagement score (0-100)
        engagement_score = 0
        if status == "sent":
            engagement_score = 10
        elif status == "opened":
            engagement_score = 40 + min(total_opens * 5, 30)
        elif status == "clicked":
            engagement_score = 70 + min(total_clicks * 5, 30)
        elif status == "bounced":
            engagement_score = 0
        elif status == "unsubscribed":
            engagement_score = 0
        
        # Get workflow progress
        current_node = None
        node_id = None
        # TODO: Query WorkflowInstance to get current node
        
        # Count total emails received
        q_emails = await self.db.execute(
            sa.select(sa.func.count(EmailSend.id))
            .where(
                EmailSend.campaign_id == campaign_id,
                EmailSend.user_id == user.id
            )
        )
        emails_received = q_emails.scalar_one() or 0
        
        return RecipientStatus(
            user_id=user.id,
            email=user.email,
            name=f"{user.first_name or ''} {user.last_name or ''}".strip() or None,
            status=status,
            engagement_score=engagement_score,
            sent_at=email_send.created_at,
            opened_at=opened_at,
            clicked_at=clicked_at,
            last_activity_at=last_activity_at,
            current_workflow_node=current_node,
            workflow_node_id=node_id,
            total_opens=total_opens,
            total_clicks=total_clicks,
            emails_received=emails_received
        )
    
    async def _calculate_recipient_summary(self, campaign_id: UUID) -> dict:
        """Calculate summary statistics for recipients."""
        
        # Get status counts
        q_sent = await self.db.execute(
            sa.select(sa.func.count(EmailSend.id))
            .where(EmailSend.campaign_id == campaign_id)
        )
        sent = q_sent.scalar_one() or 0
        
        q_opened = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.OPENED
            )
        )
        opened = q_opened.scalar_one() or 0
        
        q_clicked = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .select_from(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                Event.type == EventTypeEnum.CLICKED
            )
        )
        clicked = q_clicked.scalar_one() or 0
        
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
        
        return {
            'sent': sent,
            'opened': opened,
            'clicked': clicked,
            'bounced': bounced,
            'unsubscribed': 0  # TODO: Implement
        }
    
    async def get_recipient_detail(self, campaign_id: UUID, user_id: UUID) -> RecipientDetail:
        """Get detailed information about a specific recipient."""
        
        # Get user
        q_user = await self.db.execute(
            sa.select(User).where(User.id == user_id)
        )
        user = q_user.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get email sends for this user in this campaign
        q_sends = await self.db.execute(
            sa.select(EmailSend)
            .where(
                EmailSend.campaign_id == campaign_id,
                EmailSend.user_id == user_id
            )
            .order_by(EmailSend.created_at.desc())
        )
        email_sends = list(q_sends.scalars().all())
        
        if not email_sends:
            raise ValueError(f"No emails sent to user {user_id} in campaign {campaign_id}")
        
        # Build basic status from most recent send
        latest_send = email_sends[0]
        basic_status = await self._build_recipient_status(latest_send, user, campaign_id)
        
        # Get all events for this user in this campaign
        q_events = await self.db.execute(
            sa.select(Event)
            .join(EmailSend, Event.email_send_id == EmailSend.id)
            .where(
                EmailSend.campaign_id == campaign_id,
                EmailSend.user_id == user_id
            )
            .order_by(Event.created_at.desc())
        )
        events = list(q_events.scalars().all())
        
        # Build event timeline
        event_timeline = [
            {
                'type': event.type,
                'timestamp': event.created_at.isoformat(),
                'metadata': event.metadata or {}
            }
            for event in events
        ]
        
        # Build email history
        email_history = [
            {
                'subject': send.data.get('subject', 'No subject') if send.data else 'No subject',
                'sent_at': send.created_at.isoformat(),
                'status': send.status,
                'template_id': str(send.metadata.get('template_id')) if send.metadata and send.metadata.get('template_id') else None
            }
            for send in email_sends
        ]
        
        # Get user attributes
        attributes = {}
        if user.attributes:
            attributes = user.attributes.data or {}
        
        return RecipientDetail(
            user_id=user.id,
            email=basic_status.email,
            name=basic_status.name,
            status=basic_status.status,
            engagement_score=basic_status.engagement_score,
            sent_at=basic_status.sent_at,
            opened_at=basic_status.opened_at,
            clicked_at=basic_status.clicked_at,
            last_activity_at=basic_status.last_activity_at,
            current_workflow_node=basic_status.current_workflow_node,
            workflow_node_id=basic_status.workflow_node_id,
            total_opens=basic_status.total_opens,
            total_clicks=basic_status.total_clicks,
            emails_received=basic_status.emails_received,
            events=event_timeline,
            emails=email_history,
            attributes=attributes
        )
    
    # ========================================================================
    # WORKFLOW VISUALIZATION METHODS
    # ========================================================================
    
    async def get_workflow_visualization(self, campaign_id: UUID) -> WorkflowVisualization:
        """Get workflow structure with execution statistics."""
        
        # Get campaign with workflow
        campaign = await self._get_campaign(campaign_id)
        
        # Get workflow
        q_workflow = await self.db.execute(
            sa.select(Workflow).where(Workflow.campaign_id == campaign_id)
        )
        workflow = q_workflow.scalar_one_or_none()
        
        if not workflow:
            raise ValueError(f"No workflow found for campaign {campaign_id}")
        
        # Get workflow nodes
        q_nodes = await self.db.execute(
            sa.select(WorkflowNode)
            .where(WorkflowNode.workflow_id == workflow.id)
            .order_by(WorkflowNode.created_at)
        )
        nodes = list(q_nodes.scalars().all())
        
        # Build node data
        node_data = []
        node_stats = []
        
        for node in nodes:
            # Add node structure
            node_data.append({
                'id': str(node.id),
                'type': node.type,
                'label': node.config.get('label', node.type) if node.config else node.type,
                'position': node.config.get('position', {'x': 0, 'y': 0}) if node.config else {'x': 0, 'y': 0},
                'config': node.config or {}
            })
            
            # Calculate node statistics
            stats = await self._calculate_node_stats(node.id, campaign_id)
            node_stats.append(stats)
        
        # Build edges (connections)
        edges = []
        for node in nodes:
            if node.config and 'next' in node.config:
                edges.append({
                    'from': str(node.id),
                    'to': str(node.config['next'])
                })
        
        # Get overall workflow instance stats
        q_instances = await self.db.execute(
            sa.select(
                sa.func.count(WorkflowInstance.id).label('total'),
                sa.func.count(sa.case((WorkflowInstance.status == 'running', 1))).label('active'),
                sa.func.count(sa.case((WorkflowInstance.status == 'completed', 1))).label('completed')
            )
            .where(WorkflowInstance.workflow_id == workflow.id)
        )
        instance_stats = q_instances.one()
        
        return WorkflowVisualization(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            is_active=workflow.is_active,
            nodes=node_data,
            edges=edges,
            node_stats=node_stats,
            total_instances=instance_stats.total or 0,
            active_instances=instance_stats.active or 0,
            completed_instances=instance_stats.completed or 0,
            failed_instances=0  # TODO: Track failed instances
        )
    
    async def _calculate_node_stats(self, node_id: UUID, campaign_id: UUID) -> WorkflowNodeStats:
        """Calculate statistics for a specific workflow node."""
        
        # Get node info
        q_node = await self.db.execute(
            sa.select(WorkflowNode).where(WorkflowNode.id == node_id)
        )
        node = q_node.scalar_one()
        
        # Count active leads at this node
        # Count active leads at this node by looking at current running steps
        q_active = await self.db.execute(
            sa.select(sa.func.count(WorkflowStep.id))
            .where(
                WorkflowStep.node_id == node_id,
                WorkflowStep.status == "running"
            )
        )
        leads_active = q_active.scalar_one() or 0
        
        # Count completed (passed through)
        # TODO: Implement node history tracking
        leads_completed = 0
        
        # Count failed
        leads_failed = 0
        
        # Calculate average time at node
        avg_time = None  # TODO: Implement timing tracking
        
        # Calculate success rate
        total = leads_active + leads_completed + leads_failed
        success_rate = (leads_completed / total * 100) if total > 0 else 0.0
        
        return WorkflowNodeStats(
            node_id=node.id,
            node_type=node.type,
            node_label=node.config.get('label', node.type) if node.config else node.type,
            leads_active=leads_active,
            leads_completed=leads_completed,
            leads_failed=leads_failed,
            avg_time_at_node=avg_time,
            success_rate=round(success_rate, 2)
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
        """Send test email to specified recipients using configured provider."""
        
        # Verify campaign exists
        campaign = await self._get_campaign(campaign_id)
        
        # Get template
        template = None
        if template_id:
            res_template = await self.db.execute(
                sa.select(EmailTemplate).where(EmailTemplate.id == template_id)
            )
            template = res_template.scalar_one_or_none()
        
        if not template and use_campaign_workflow:
            # Try to find a template from the workflow
            res_node = await self.db.execute(
                sa.select(WorkflowNode)
                .join(Workflow, WorkflowNode.workflow_id == Workflow.id)
                .where(
                    Workflow.campaign_id == campaign_id,
                    WorkflowNode.type == 'email'
                )
                .limit(1)
            )
            node = res_node.scalar_one_or_none()
            if node and node.config and node.config.get('template_id'):
                res_template = await self.db.execute(
                    sa.select(EmailTemplate).where(EmailTemplate.id == UUID(node.config['template_id']))
                )
                template = res_template.scalar_one_or_none()
        
        if not template:
            # Fallback to any template if none found
            res_template = await self.db.execute(sa.select(EmailTemplate).limit(1))
            template = res_template.scalar_one_or_none()
            
        if not template:
            raise ValueError("No email template found for test email")
            
        provider = await get_email_provider(self.db)
        
        success_count = 0
        errors = []
        
        for email in recipient_emails:
            try:
                # Basic rendering for test email
                # In a real send, this would use the recipient's actual attributes
                subject = f"[TEST] {template.subject}"
                body = template.html_body
                
                message_id = await provider.send_email(
                    to_email=email,
                    subject=subject,
                    html_body=body,
                    metadata={
                        "test_email": "true",
                        "campaign_id": str(campaign_id),
                        "template_id": str(template.id)
                    }
                )
                success_count += 1
            except Exception as e:
                errors.append(f"Failed to send to {email}: {str(e)}")
        
        return {
            'success': success_count > 0,
            'message': f'Test email sent to {success_count}/{len(recipient_emails)} recipients',
            'details': {
                'recipients': recipient_emails,
                'template_id': str(template.id),
                'success_count': success_count,
                'errors': errors
            }
        }
    
    async def duplicate_campaign(
        self,
        campaign_id: UUID,
        new_name: str,
        copy_workflow: bool = True,
        copy_contacts: bool = False,
        owner_id: UUID = None
    ) -> dict:
        """Duplicate an existing campaign."""
        
        # Get original campaign
        original = await self._get_campaign(campaign_id)
        
        # Create new campaign
        new_campaign = Campaign(
            name=new_name,
            description=f"Copy of {original.name}",
            owner_id=owner_id or original.owner_id,
            is_active=False,  # Start as inactive
            warmup_config=original.warmup_config,
            retry_config=original.retry_config
        )
        
        if copy_contacts:
            new_campaign.contact_list_id = original.contact_list_id
        
        self.db.add(new_campaign)
        await self.db.commit()
        await self.db.refresh(new_campaign)
        
        # Copy workflow if requested
        if copy_workflow:
            q_workflow = await self.db.execute(
                sa.select(Workflow).where(Workflow.campaign_id == campaign_id)
            )
            original_workflow = q_workflow.scalar_one_or_none()
            
            if original_workflow:
                # TODO: Implement workflow duplication
                pass
        
        return {
            'success': True,
            'campaign_id': str(new_campaign.id),
            'name': new_campaign.name
        }
    
    async def export_campaign_data(
        self,
        campaign_id: UUID,
        format: str = "csv",
        include_recipients: bool = True,
        include_analytics: bool = True,
        include_events: bool = False
    ) -> str:
        """Export campaign data in specified format."""
        
        # Verify campaign exists
        campaign = await self._get_campaign(campaign_id)
        
        if format == "csv":
            return await self._export_csv(
                campaign_id,
                include_recipients,
                include_analytics,
                include_events
            )
        elif format == "json":
            return await self._export_json(
                campaign_id,
                include_recipients,
                include_analytics,
                include_events
            )
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _export_csv(
        self,
        campaign_id: UUID,
        include_recipients: bool,
        include_analytics: bool,
        include_events: bool
    ) -> str:
        """Export campaign data as CSV."""
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if include_recipients:
            # Export recipients
            recipients_response = await self.get_recipients(campaign_id, page=1, page_size=10000)
            
            writer.writerow(['Email', 'Name', 'Status', 'Engagement Score', 'Sent At', 'Last Activity'])
            for recipient in recipients_response.recipients:
                writer.writerow([
                    recipient.email,
                    recipient.name or '',
                    recipient.status,
                    recipient.engagement_score,
                    recipient.sent_at.isoformat() if recipient.sent_at else '',
                    recipient.last_activity_at.isoformat() if recipient.last_activity_at else ''
                ])
        
        return output.getvalue()
    
    async def _export_json(
        self,
        campaign_id: UUID,
        include_recipients: bool,
        include_analytics: bool,
        include_events: bool
    ) -> str:
        """Export campaign data as JSON."""
        
        data = {}
        
        if include_analytics:
            analytics = await self.get_analytics(campaign_id)
            data['analytics'] = analytics.dict()
        
        if include_recipients:
            recipients = await self.get_recipients(campaign_id, page=1, page_size=10000)
            data['recipients'] = [r.dict() for r in recipients.recipients]
        
        return json.dumps(data, indent=2, default=str)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _get_campaign(self, campaign_id: UUID) -> Campaign:
        """Get campaign or raise error."""
        q = await self.db.execute(
            sa.select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = q.scalar_one_or_none()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        return campaign
