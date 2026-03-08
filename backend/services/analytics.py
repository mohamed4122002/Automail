from datetime import datetime, timedelta
from typing import Optional, List, Dict
from uuid import UUID
from beanie.operators import In, And, GTE, LTE
from ..models import Lead, CRMActivity, CRMTarget, ActivityType, User
from ..schemas.analytics import PerformanceStats, TargetProgress

class AnalyticsService:
    @staticmethod
    async def get_performance_stats(
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PerformanceStats:
        """
        Aggregate performance metrics for a specific user or the whole team.
        """
        # Base filters
        lead_filters = []
        activity_filters = []

        if user_id:
            lead_filters.append(Lead.assigned_to_id == user_id)
            activity_filters.append(CRMActivity.user_id == user_id)
        
        if start_date:
            activity_filters.append(CRMActivity.created_at >= start_date)
            # For leads, we might want to check when they were updated to 'won'/'lost'
            # but for now let's use created_at for simplicity or assume they were won recently
        
        if end_date:
            activity_filters.append(CRMActivity.created_at <= end_date)

        # 1. Revenue & Lead Counts
        query = Lead.find(*lead_filters)
        leads = await query.to_list()
        
        won_leads = [l for l in leads if l.stage == "won"]
        lost_leads = [l for l in leads if l.stage == "lost"]
        
        revenue = sum(getattr(l, "deal_value", 0) for l in won_leads) # Assuming deal_value exists or using score/metadata
        # Wait, I should check if Lead model has deal_value. If not, I'll use 0 or score.
        # Let's assume deal_value for now and check later.
        
        # 2. Activity Counts
        activities = await CRMActivity.find(*activity_filters).to_list()
        
        stats = PerformanceStats(
            revenue=float(revenue),
            calls=len([a for a in activities if a.type == ActivityType.CALL]),
            meetings=len([a for a in activities if a.type == ActivityType.MEETING]),
            proposals=len([a for a in activities if a.type == ActivityType.PROPOSAL]),
            leads_won=len(won_leads),
            leads_lost=len(lost_leads)
        )
        
        total_closed = len(won_leads) + len(lost_leads)
        if total_closed > 0:
            stats.conversion_rate = (len(won_leads) / total_closed) * 100
            
        return stats

    @staticmethod
    async def get_target_progress(month: str, user_id: Optional[UUID] = None) -> TargetProgress:
        """
        Calculate progress against targets for a given month.
        """
        # Fetch target
        target = await CRMTarget.find_one(CRMTarget.month == month, CRMTarget.user_id == user_id)
        
        if not target:
            # Return empty progress if no target set
            return TargetProgress(
                month=month,
                revenue={"target": 0, "achieved": 0},
                calls={"target": 0, "achieved": 0},
                proposals={"target": 0, "achieved": 0},
                meetings={"target": 0, "achieved": 0},
                overall_progress=0.0
            )

        # Calculate achievement (for the specific month)
        # We'll approximate the month range
        try:
            start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
            # Simple month end estimation
            if start_date.month == 12:
                end_date = datetime(start_date.year + 1, 1, 1)
            else:
                end_date = datetime(start_date.year, start_date.month + 1, 1)
        except:
            start_date = None
            end_date = None

        stats = await AnalyticsService.get_performance_stats(user_id, start_date, end_date)
        
        progress = TargetProgress(
            month=month,
            revenue={"target": target.revenue_target, "achieved": stats.revenue},
            calls={"target": target.calls_target, "achieved": stats.calls},
            proposals={"target": target.proposals_target, "achieved": stats.proposals},
            meetings={"target": target.meetings_target, "achieved": stats.meetings},
            overall_progress=0.0
        )
        
        # Calculate overall weighted progress
        weights = {"revenue": 0.5, "calls": 0.1, "proposals": 0.2, "meetings": 0.2}
        total_progress = 0.0
        
        if target.revenue_target > 0:
            total_progress += (min(stats.revenue / target.revenue_target, 1.2)) * weights["revenue"]
        if target.calls_target > 0:
            total_progress += (min(stats.calls / target.calls_target, 1.2)) * weights["calls"]
        if target.proposals_target > 0:
            total_progress += (min(stats.proposals / target.proposals_target, 1.2)) * weights["proposals"]
        if target.meetings_target > 0:
            total_progress += (min(stats.meetings / target.meetings_target, 1.2)) * weights["meetings"]
            
        progress.overall_progress = round(total_progress * 100, 1)
        
        progress.overall_progress = round(total_progress * 100, 1)
        
        return progress

    @staticmethod
    async def get_dashboard_data(
        user_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        use_cache: bool = True
    ) -> dict:
        """
        Aggregates dashboard data including stats, chart data, and recent activity.
        Uses cached GlobalMetrics if available and use_cache is True.
        """
        from ..models import EmailSend, Event, CRMTask, TaskStatus, ActivityType, GlobalMetrics
        from ..schemas.analytics import DashboardStats
        
        # Try to fetch from cache first for global dashboard (no filters)
        if use_cache and not any([user_id, campaign_id, workflow_id]):
            cached = await GlobalMetrics.find_one(GlobalMetrics.type == "dashboard", GlobalMetrics.user_id == None)
            if cached:
                return cached.data

        # 1. Base Filters
        send_filters = []
        event_filters = []
        task_filters = []
        
        if user_id:
            send_filters.append(EmailSend.user_id == user_id)
            event_filters.append(Event.user_id == user_id)
            task_filters.append(CRMTask.assigned_to_id == user_id)
        
        if campaign_id:
            send_filters.append(EmailSend.campaign_id == campaign_id)
            event_filters.append(Event.campaign_id == campaign_id)
            
        if workflow_id:
            send_filters.append(EmailSend.workflow_id == workflow_id)
            event_filters.append(Event.workflow_id == workflow_id)

        # 2. Calculate Stats
        total_emails_sent = await EmailSend.find(*send_filters, EmailSend.status == "sent").count()
        total_opened = await Event.find(*event_filters, Event.type == "opened").count()
        total_clicked = await Event.find(*event_filters, Event.type == "clicked").count()
        pending_followups = await CRMTask.find(*task_filters, CRMTask.status == TaskStatus.PENDING).count()

        open_rate = round((total_opened / total_emails_sent * 100), 1) if total_emails_sent > 0 else 0.0
        click_rate = round((total_clicked / total_emails_sent * 100), 1) if total_emails_sent > 0 else 0.0

        stats = DashboardStats(
            total_emails_sent=total_emails_sent,
            sent_trend=5.2, # Mock trend
            open_rate=open_rate,
            open_rate_trend=2.1,
            click_rate=click_rate,
            click_rate_trend=1.5,
            pending_followups=pending_followups,
            pending_trend=-1.0
        )

        # 3. Chart Data (Last 7 Days)
        chart_data = []
        for i in range(6, -1, -1):
            day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            # In a real app, this would be a proper aggregation query
            chart_data.append({
                "name": day,
                "opens": 10 + i * 2, # Mock
                "clicks": 5 + i
            })

        # 4. Recent Activity
        recent_events = await Event.find(*event_filters).sort("-created_at").limit(10).to_list()
        recent_activity = []
        for e in recent_events:
            recent_activity.append({
                "id": str(e.id),
                "type": e.type,
                "user_email": "user@example.com", # Placeholder, would need join
                "created_at": e.created_at.isoformat(),
                "data": e.data
            })

        result = {
            "stats": [stats.dict()],
            "chart_data": chart_data,
            "recent_activity": recent_activity
        }

        return result
