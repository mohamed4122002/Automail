"""
Dashboard personal stats endpoint — Phase 2.
GET /api/v1/dashboard/me
Returns a personal summary for the logged-in user:
  - my_leads_count
  - my_meetings_today
  - my_overdue_tasks
  - recent_activity list
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, date
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from ..models import Lead, CRMTask, CRMActivity, TaskStatus
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class PersonalStats(BaseModel):
    my_leads_count: int
    my_meetings_today: int
    my_overdue_tasks: int
    recent_activity: List[dict]


@router.get("/me", response_model=PersonalStats)
async def get_my_dashboard(
    user_id: UUID = Depends(get_current_user_id)
):
    """Personal stats for the logged-in team member."""
    today = datetime.now(timezone.utc).date()

    # Count my leads
    my_leads = await Lead.find(Lead.assigned_to_id == user_id).to_list()
    my_leads_count = len(my_leads)

    # Meetings today = CRMActivities with type 'meeting' today
    all_activities = await CRMActivity.find(CRMActivity.user_id == user_id).to_list()
    my_meetings_today = sum(
        1 for a in all_activities
        if a.type in ("meeting", "MEETING")
        and a.created_at.date() == today
    )

    # Overdue tasks: due_date < today and status not done/cancelled
    all_tasks = await CRMTask.find(CRMTask.assigned_to_id == user_id).to_list()
    my_overdue_tasks = sum(
        1 for t in all_tasks
        if t.due_date and t.due_date.date() < today
        and t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
    )

    # Recent activity (last 5)
    recent = sorted(all_activities, key=lambda a: a.created_at, reverse=True)[:5]
    recent_activity = [
        {
            "id": str(a.id),
            "type": a.type,
            "content": a.content,
            "lead_id": str(a.lead_id),
            "created_at": a.created_at.isoformat(),
        }
        for a in recent
    ]

    return PersonalStats(
        my_leads_count=my_leads_count,
        my_meetings_today=my_meetings_today,
        my_overdue_tasks=my_overdue_tasks,
        recent_activity=recent_activity,
    )
