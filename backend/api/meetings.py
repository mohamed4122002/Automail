from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from ..models import User, UserRole, OAuthToken, CRMActivity, ActivityType
from ..auth import get_current_user, get_current_active_user
from ..services.google_calendar import GoogleCalendarService
from ..schemas.users import UserProfile
from ..schemas.utils import orm_list_to_pydantic

router = APIRouter(prefix="/meetings", tags=["meetings"])

def can_assign_to(assigner_role: UserRole, assignee_role: UserRole) -> bool:
    """Check if the assigner's role allows them to assign meetings to the assignee."""
    hierarchy = {
        UserRole.SUPER_ADMIN: [UserRole.ADMIN, UserRole.MANAGER, UserRole.SALES_LEAD, UserRole.TEAM_MEMBER],
        UserRole.ADMIN: [UserRole.MANAGER, UserRole.SALES_LEAD, UserRole.TEAM_MEMBER],
        UserRole.MANAGER: [UserRole.TEAM_MEMBER],
        UserRole.SALES_LEAD: [UserRole.TEAM_MEMBER],
        UserRole.TEAM_MEMBER: []
    }
    return assignee_role in hierarchy.get(assigner_role, [])

@router.get("/assignable-users", response_model=List[UserProfile])
async def get_assignable_users(current_user: User = Depends(get_current_active_user)):
    """List users that the current user can assign meetings to."""
    all_users = await User.find_all().to_list()
    assignable = [u for u in all_users if can_assign_to(current_user.role, u.role) and u.id != current_user.id]
    return orm_list_to_pydantic(assignable, UserProfile)

class MeetingCreate(BaseModel):
    assignee_id: UUID
    summary: str
    description: str
    start_time: datetime
    end_time: datetime

@router.post("/assign")
async def assign_meeting(
    payload: MeetingCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Assign a meeting to another user using the assigner's Google Calendar."""
    assignee = await User.find_one(User.id == payload.assignee_id)
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")
        
    if not can_assign_to(current_user.role, assignee.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to assign meetings to a {assignee.role}"
        )
        
    # Check if assigner has Google Calendar connected
    token = await OAuthToken.find_one(
        OAuthToken.user_id == current_user.id,
        OAuthToken.provider == "google"
    )
    if not token:
        raise HTTPException(
            status_code=400,
            detail="You must connect your Google Calendar first."
        )
        
    try:
        # Create event and invite assignee
        event = await GoogleCalendarService.create_event(
            user_id=current_user.id,
            summary=payload.summary,
            description=payload.description,
            start_time=payload.start_time,
            end_time=payload.end_time,
            attendees=[assignee.email]
        )
        
        # Log activity
        activity = CRMActivity(
            lead_id=assignee.id, 
            user_id=current_user.id,
            type=ActivityType.MEETING,
            content=f"Scheduled meeting: {payload.summary}",
            metadata={
                "event_id": event.get("id"),
                "assignee_email": assignee.email,
                "start": payload.start_time.isoformat()
            }
        )
        await activity.insert()
        
        return {"status": "success", "event_id": event.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/today")
async def get_today_meetings(current_user: User = Depends(get_current_active_user)):
    """Fetch meetings scheduled for today from CRMActivity logs."""
    from datetime import datetime, time
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    today_end = datetime.combine(datetime.utcnow().date(), time.max)
    
    # We look for activities of type MEETING where metadata.start is within today
    # Note: metadata.start is stored as isoformat string in assign_meeting
    activities = await CRMActivity.find(
        CRMActivity.user_id == current_user.id,
        CRMActivity.type == ActivityType.MEETING,
        CRMActivity.created_at >= today_start # Simple fallback if specific start time is hard to query in JSON
    ).to_list()
    
    # More precise filter if metadata has 'start'
    results = []
    for a in activities:
        start_str = a.metadata.get("start")
        if start_str:
            try:
                start_dt = datetime.fromisoformat(start_str)
                if today_start <= start_dt <= today_end:
                    # Enrich with Lead name
                    from ..models import Lead
                    lead = await Lead.find_one(Lead.id == a.lead_id)
                    results.append({
                        "id": str(a.id),
                        "lead_id": str(a.lead_id),
                        "company_name": lead.company_name if lead else "Unknown",
                        "title": a.content,
                        "start_time": start_dt.isoformat()
                    })
            except Exception:
                continue
    return results
