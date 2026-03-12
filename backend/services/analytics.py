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
        lead_match = {}
        activity_match = {}

        if user_id:
            lead_match["assigned_to_id"] = user_id
            activity_match["user_id"] = user_id
        
        if start_date:
            activity_match["created_at"] = {"$gte": start_date}
        if end_date:
            if "created_at" in activity_match:
                activity_match["created_at"]["$lte"] = end_date
            else:
                activity_match["created_at"] = {"$lte": end_date}

        # 1. Revenue & Lead Counts via Aggregation
        lead_pipeline = [
            {"$match": lead_match} if lead_match else {"$match": {}},
            {"$group": {
                "_id": "$stage",
                "count": {"$sum": 1},
                "revenue": {"$sum": {"$cond": [{"$eq": ["$stage", "won"]}, "$deal_value", 0]}}
            }}
        ]
        
        lead_results = await Lead.get_motor_collection().aggregate(lead_pipeline).to_list(length=None)
        
        won_leads = 0
        lost_leads = 0
        revenue = 0.0
        
        for r in lead_results:
            if r["_id"] == "won":
                won_leads = r["count"]
                revenue = r["revenue"]
            elif r["_id"] == "lost":
                lost_leads = r["count"]

        # 2. Activity Counts via Aggregation
        act_pipeline = [
            {"$match": activity_match} if activity_match else {"$match": {}},
            {"$group": {
                "_id": "$type",
                "count": {"$sum": 1}
            }}
        ]
        
        act_results = await CRMActivity.get_motor_collection().aggregate(act_pipeline).to_list(length=None)
        
        act_counts = {r["_id"]: r["count"] for r in act_results}
        
        stats = PerformanceStats(
            revenue=float(revenue),
            calls=act_counts.get(ActivityType.CALL.value, 0),
            meetings=act_counts.get(ActivityType.MEETING.value, 0),
            proposals=act_counts.get(ActivityType.PROPOSAL.value, 0),
            leads_won=won_leads,
            leads_lost=lost_leads
        )
        
        total_closed = won_leads + lost_leads
        if total_closed > 0:
            stats.conversion_rate = (won_leads / total_closed) * 100
            
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

    @staticmethod
    async def get_action_center_data(user: User) -> dict:
        """
        Aggregates tasks, leads needing attention, and notifications.
        Role-based:
        - Manager: Unassigned leads, team-wide overdue tasks.
        - Team Member: Assigned overdue tasks, inactive leads (>4 days).
        """
        from ..models import CRMTask, Lead, CRMNotification, TaskStatus
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        actions = []
        is_manager = user.role in ["admin", "super_admin", "manager"]
        
        # 1. Tasks section
        task_filters = [CRMTask.status == TaskStatus.PENDING]
        if not is_manager:
            task_filters.append(CRMTask.assigned_to_id == user.id)
            
        pending_tasks = await CRMTask.find(*task_filters).to_list()
        for task in pending_tasks:
            is_overdue = task.due_date and task.due_date < now
            severity = "high" if is_overdue else "medium"
            actions.append({
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "type": "task",
                "severity": severity,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "link": f"/leads/{task.lead_id}?tab=tasks",
                "metadata": {"lead_id": str(task.lead_id)}
            })

        # 2. Leads section
        if is_manager:
            # Unassigned leads for managers
            unassigned_leads = await Lead.find(Lead.assigned_to_id == None).to_list()
            for lead in unassigned_leads:
                actions.append({
                    "id": str(lead.id),
                    "title": f"Assign Lead: {lead.company_name}",
                    "description": f"Lead from {lead.source} needs an owner.",
                    "type": "lead_assignment",
                    "severity": "high",
                    "due_date": lead.created_at.isoformat(),
                    "link": f"/leads/{lead.id}",
                    "metadata": {"source": lead.source}
                })
        else:
            # Inactive leads for team members (>4 days)
            four_days_ago = now - timedelta(days=4)
            inactive_leads = await Lead.find(
                Lead.assigned_to_id == user.id,
                Lead.last_activity_at < four_days_ago,
                Lead.stage != "won",
                Lead.stage != "lost"
            ).to_list()
            
            for lead in inactive_leads:
                actions.append({
                    "id": str(lead.id),
                    "title": f"Stale Lead: {lead.company_name}",
                    "description": "No activity recorded in over 4 days. Reach out now.",
                    "type": "inactive_lead",
                    "severity": "medium",
                    "due_date": lead.last_activity_at.isoformat(),
                    "link": f"/leads/{lead.id}",
                    "metadata": {"last_activity": lead.last_activity_at.isoformat()}
                })

        # 3. Notifications section (Unread)
        notifications = await CRMNotification.find(
            CRMNotification.user_id == user.id,
            CRMNotification.is_read == False
        ).sort(-CRMNotification.created_at).limit(10).to_list()
        
        for n in notifications:
            actions.append({
                "id": str(n.id),
                "title": n.title,
                "description": n.message,
                "type": "notification",
                "severity": "low",
                "due_date": n.created_at.isoformat(),
                "link": n.link,
                "metadata": {"notif_type": n.type}
            })

        # Sort by severity then date
        severity_map = {"high": 0, "medium": 1, "low": 2}
        actions.sort(key=lambda x: (severity_map.get(x["severity"], 3), x["due_date"] or ""))

        return {
            "actions": actions,
            "counts": {
                "high": len([a for a in actions if a["severity"] == "high"]),
                "medium": len([a for a in actions if a["severity"] == "medium"]),
                "low": len([a for a in actions if a["severity"] == "low"]),
                "total": len(actions)
            },
            "role": user.role
        }

    @staticmethod
    async def get_reputation_stats(user_id: Optional[UUID] = None) -> dict:
        """
        Calculates sender reputation based on email activity.
        """
        from ..models import EmailSend, Event
        
        # Base filters
        send_filters = []
        event_filters = []
        if user_id:
            send_filters.append(EmailSend.user_id == user_id)
            event_filters.append(Event.user_id == user_id)

        # 1. Gather metrics
        total_sent = await EmailSend.find(*send_filters, EmailSend.status == "sent").count()
        total_opened = await Event.find(*event_filters, Event.type == "opened").count()
        total_clicked = await Event.find(*event_filters, Event.type == "clicked").count()
        total_bounced = await Event.find(*event_filters, Event.type == "bounced").count()
        total_unsubscribed = await Event.find(*event_filters, Event.type == "unsubscribed").count()

        # 2. Calculate rates
        open_rate = round((total_opened / total_sent * 100), 1) if total_sent > 0 else 0.0
        click_rate = round((total_clicked / total_sent * 100), 1) if total_sent > 0 else 0.0
        bounce_rate = round((total_bounced / total_sent * 100), 1) if total_sent > 0 else 0.0
        unsubscribe_rate = round((total_unsubscribed / total_sent * 100), 1) if total_sent > 0 else 0.0

        # 3. Calculate score (Simplified algorithm)
        # Perfect score 100
        score = 85 # Base
        
        # Bonuses
        if open_rate > 20: score += 5
        if click_rate > 5: score += 5
        
        # Penalties
        score -= (bounce_rate * 5)
        score -= (unsubscribe_rate * 10)
        
        # Range cap
        score = max(0, min(100, int(score)))
        
        # Status
        status = "Excellent"
        if score < 70: status = "Good"
        if score < 50: status = "Fair"
        if score < 30: status = "Poor"

        # Warnings
        warnings = []
        if bounce_rate > 2.0:
            warnings.append(f"High bounce rate ({bounce_rate}%). Clean your list to avoid blacklisting.")
        if unsubscribe_rate > 1.0:
            warnings.append(f"High unsubscribe rate ({unsubscribe_rate}%). Your content may be irrelevant.")
        if score < 50:
            warnings.append("Low reputation detected. Deliverability is at risk.")

        return {
            "score": score,
            "status": status,
            "metrics": {
                "total_emails_sent": total_sent,
                "open_rate": open_rate,
                "click_rate": click_rate,
                "bounce_rate": bounce_rate,
                "unsubscribe_rate": unsubscribe_rate
            },
            "warnings": warnings
        }
