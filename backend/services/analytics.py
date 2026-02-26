import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from ..models import Event, User, Workflow, Campaign, EventTypeEnum, WorkflowInstance


import json
import redis.asyncio as aioredis
from ..config import settings

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Use asynchronous redis for non-blocking I/O
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get_dashboard_stats(
        self,
        owner_id: UUID,
        workflow_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get dashboard statistics with optional workflow/campaign filtering.
        Caches results in Redis for 5 minutes.
        """
        # Create unique cache key
        cache_key = f"analytics:stats:{owner_id}:{workflow_id}:{campaign_id}:{days}"
        
        # Try cache hit
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            # Fallback to DB if Redis is down
            logger.error(f"Redis cache hit failed: {e}")
            pass

        since = datetime.utcnow() - timedelta(days=days)
        
        # Build base filters
        event_filters = [Event.created_at >= since]
        
        if workflow_id:
            event_filters.append(Event.workflow_id == workflow_id)
        
        if campaign_id:
            event_filters.append(Event.campaign_id == campaign_id)
        
        # Total emails sent
        q_sent = await self.db.execute(
            sa.select(sa.func.count(Event.id))
            .where(*event_filters, Event.type == EventTypeEnum.SENT)
        )
        total_sent = q_sent.scalar_one() or 0
        
        # Unique opens
        q_opens = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .where(*event_filters, Event.type == EventTypeEnum.OPENED)
        )
        unique_opens = q_opens.scalar_one() or 0
        
        # Unique clicks
        q_clicks = await self.db.execute(
            sa.select(sa.func.count(sa.func.distinct(Event.user_id)))
            .where(*event_filters, Event.type == EventTypeEnum.CLICKED)
        )
        unique_clicks = q_clicks.scalar_one() or 0
        
        # Bounces
        q_bounces = await self.db.execute(
            sa.select(sa.func.count(Event.id))
            .where(*event_filters, Event.type == EventTypeEnum.BOUNCED)
        )
        bounces = q_bounces.scalar_one() or 0
        
        # Unsubscribes
        q_unsubscribes = await self.db.execute(
            sa.select(sa.func.count(Event.id))
            .where(*event_filters, Event.type == EventTypeEnum.UNSUBSCRIBED)
        )
        unsubscribes = q_unsubscribes.scalar_one() or 0
        
        # Calculate rates
        open_rate = (unique_opens / total_sent * 100) if total_sent > 0 else 0
        click_rate = (unique_clicks / total_sent * 100) if total_sent > 0 else 0
        bounce_rate = (bounces / total_sent * 100) if total_sent > 0 else 0
        unsubscribe_rate = (unsubscribes / total_sent * 100) if total_sent > 0 else 0
        
        # Get chart data
        chart_data = await self._get_chart_data(
            since=since,
            workflow_id=workflow_id,
            campaign_id=campaign_id
        )
        
        result = {
            "stats": [{
                "total_emails_sent": total_sent,
                "unique_opens": unique_opens,
                "unique_clicks": unique_clicks,
                "bounces": bounces,
                "unsubscribes": unsubscribes,
                "open_rate": round(open_rate, 1),
                "click_rate": round(click_rate, 1),
                "bounce_rate": round(bounce_rate, 1),
                "unsubscribe_rate": round(unsubscribe_rate, 1),
                "sent_trend": 0,
                "open_trend": 0,
                "click_trend": 0
            }],
            "chart_data": chart_data,
            "recent_activity": []
        }

        # Cache for 5 minutes (300 seconds)
        try:
            await self.redis.setex(cache_key, 300, json.dumps(result))
        except Exception:
            pass

        return result

    async def _get_chart_data(
        self,
        since: datetime,
        workflow_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get time-series chart data with optional filtering.
        Optimized to use a single SQL query instead of looping through days.
        """
        # Build base filters
        filters = [
            Event.created_at >= since,
            Event.type.in_([EventTypeEnum.OPENED, EventTypeEnum.CLICKED])
        ]
        
        if workflow_id:
            filters.append(Event.workflow_id == workflow_id)
        if campaign_id:
            filters.append(Event.campaign_id == campaign_id)

        # ONE query replaces N*2 queries (where N is days_back)
        result = await self.db.execute(
            sa.select(
                sa.func.date_trunc("day", Event.created_at).label("day"),
                Event.type,
                sa.func.count(sa.func.distinct(Event.user_id)).label("count")
            )
            .where(*filters)
            .group_by(sa.text("day"), Event.type)
            .order_by(sa.text("day"))
        )
        rows = result.all()

        # Pivot in Python to match the expected frontend format
        days_map = {}
        
        # Initialize the map with zero values for all days in the range
        days_back = (datetime.utcnow() - since).days
        for i in range(days_back + 1):
            day_start = since + timedelta(days=i)
            key = day_start.strftime("%b %d")
            # We use ISO date as secondary key to ensure correct sorting if needed, 
            # but primary key is the display name for the frontend.
            days_map[key] = {"name": key, "opens": 0, "clicks": 0, "_raw_date": day_start.date()}

        for row in rows:
            key = row.day.strftime("%b %d")
            if key in days_map:
                if row.type == EventTypeEnum.OPENED:
                    days_map[key]["opens"] = row.count
                elif row.type == EventTypeEnum.CLICKED:
                    days_map[key]["clicks"] = row.count

        # Convert back to sorted list, removing temporary fields
        final_chart_data = []
        for key in sorted(days_map.keys(), key=lambda k: days_map[k]["_raw_date"]):
            data = days_map[key]
            del data["_raw_date"]
            final_chart_data.append(data)

        return final_chart_data

    async def compare_workflows(
        self,
        owner_id: UUID,
        workflow_ids: List[UUID],
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Compare multiple workflows side-by-side.
        
        Args:
            workflow_ids: List of workflow IDs to compare
            days: Number of days to look back
        """
        since = datetime.utcnow() - timedelta(days=days)
        comparison_data = []
        
        for workflow_id in workflow_ids:
            # Get workflow name
            q_workflow = await self.db.execute(
                sa.select(Workflow).where(Workflow.id == workflow_id)
            )
            workflow = q_workflow.scalar_one_or_none()
            
            if not workflow:
                continue
            
            # Get stats for this workflow
            stats = await self.get_dashboard_stats(
                owner_id=owner_id,  # Use passed owner_id
                workflow_id=workflow_id,
                days=days
            )
            
            comparison_data.append({
                "workflow_id": str(workflow_id),
                "workflow_name": workflow.name,
                "stats": stats["stats"][0],
                "chart_data": stats["chart_data"]
            })
        
        return {
            "workflows": comparison_data,
            "period_days": days
        }

    async def get_workflow_performance(
        self,
        owner_id: UUID,
        workflow_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed performance metrics for a specific workflow."""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        # Get workflow
        q_workflow = await self.db.execute(
            sa.select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = q_workflow.scalar_one_or_none()
        
        if not workflow:
            return {"error": "Workflow not found"}
        
        # Get instances count
        from ..models import WorkflowInstance
        q_instances = await self.db.execute(
            sa.select(sa.func.count(WorkflowInstance.id))
            .where(
                WorkflowInstance.workflow_id == workflow_id,
                WorkflowInstance.created_at >= since
            )
        )
        total_instances = q_instances.scalar_one() or 0
        
        # Get completion rate
        q_completed = await self.db.execute(
            sa.select(sa.func.count(WorkflowInstance.id))
            .where(
                WorkflowInstance.workflow_id == workflow_id,
                WorkflowInstance.status == "completed",
                WorkflowInstance.created_at >= since
            )
        )
        completed_instances = q_completed.scalar_one() or 0
        
        completion_rate = (completed_instances / total_instances * 100) if total_instances > 0 else 0
        
        # Get email stats
        stats = await self.get_dashboard_stats(
            owner_id=owner_id,  # Use passed owner_id
            workflow_id=workflow_id,
            days=days
        )
        
        return {
            "workflow_id": str(workflow_id),
            "workflow_name": workflow.name,
            "total_instances": total_instances,
            "completed_instances": completed_instances,
            "completion_rate": round(completion_rate, 1),
            "email_stats": stats["stats"][0],
            "chart_data": stats["chart_data"]
        }

    async def get_sender_reputation(self, owner_id: UUID, days: int = 30) -> Dict[str, Any]:
        """
        Calculates a sender reputation score based on email metrics.
        Returns score (0-100), metrics, and warnings.
        """
        stats_resp = await self.get_dashboard_stats(owner_id=owner_id, days=days)
        stats = stats_resp["stats"][0]
        
        open_rate = stats["open_rate"]
        click_rate = stats["click_rate"]
        bounce_rate = stats["bounce_rate"]
        unsubscribe_rate = stats["unsubscribe_rate"]
        total_sent = stats["total_emails_sent"]

        # Base score starts at 100
        score = 100.0
        warnings = []

        if total_sent < 10:
            return {
                "score": 100,
                "status": "Healthy (Low Volume)",
                "metrics": stats,
                "warnings": ["Insufficient data for accurate reputation scoring. Keep sending!"]
            }

        # Deduct for high bounce rate (Critical > 5%)
        # Each 1% above 0.5% bounce rate reduces score significantly
        if bounce_rate > 0.5:
            penalty = (bounce_rate - 0.5) * 10 
            score -= penalty
            if bounce_rate > 2.0:
                warnings.append(f"High bounce rate ({bounce_rate}%). This can damage your sender reputation.")
            if bounce_rate > 5.0:
                warnings.append("CRITICAL: Bounce rate is extremely high. Your account may be flagged for spam.")

        # Deduct for high unsubscribe rate (> 1%)
        if unsubscribe_rate > 0.5:
            penalty = (unsubscribe_rate - 0.5) * 15
            score -= penalty
            if unsubscribe_rate > 1.0:
                warnings.append(f"High unsubscribe rate ({unsubscribe_rate}%). Consider reviewing your content or targeting.")

        # Bonus/Penalty for Open Rate
        if open_rate < 15.0:
            score -= (15.0 - open_rate) * 0.5
            if open_rate < 10.0:
                warnings.append(f"Low open rate ({open_rate}%). Your emails might be landing in spam or have unengaging subjects.")
        elif open_rate > 25.0:
            score += (open_rate - 25.0) * 0.2 # Small bonus for good engagement

        # Bonus for Click Rate
        if click_rate > 5.0:
            score += (click_rate - 5.0) * 0.5

        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        
        status = "Healthy"
        if score < 85: status = "Good"
        if score < 70: status = "Fair"
        if score < 50: status = "At Risk"
        if score < 30: status = "Poor"

        return {
            "score": round(score, 1),
            "status": status,
            "metrics": stats,
            "warnings": warnings
        }
