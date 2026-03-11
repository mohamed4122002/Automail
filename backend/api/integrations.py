from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import uuid
from typing import List, Optional
from datetime import datetime

from ..services.google_calendar import GoogleCalendarService
from ..api.deps import get_current_user_id
from ..models import OAuthToken, Lead, Contact, CRMActivity, ActivityType, CRMLeadStage
from ..config import settings

router = APIRouter(prefix="/integrations", tags=["integrations"])

@router.get("/google/auth")
async def google_auth(
    redirect_uri: str,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Start Google OAuth flow."""
    flow = GoogleCalendarService.get_flow(redirect_uri)
    # Include the redirect_uri in the state so we can retrieve it in the callback
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=redirect_uri
    )
    return {"auth_url": auth_url}

@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str = Query(...), # This will contain the original redirect_uri
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Handle Google OAuth callback."""
    try:
        # The 'state' we sent was the original redirect_uri
        redirect_uri = state
        flow = GoogleCalendarService.get_flow(redirect_uri)
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        await GoogleCalendarService.save_token(user_id, credentials)
        
        return {"status": "success", "message": "Google Calendar connected successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

@router.get("/status")
async def get_integrations_status(
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Get status of active integrations."""
    tokens = await OAuthToken.find(OAuthToken.user_id == user_id).to_list()
    
    status = {
        "google_calendar": {
            "connected": any(t.provider == "google" for t in tokens),
            "email": next((t.token_data.get("email") for t in tokens if t.provider == "google"), None)
        }
    }
    
    return status

@router.delete("/google")
async def disconnect_google(
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Disconnect Google Calendar."""
    token = await OAuthToken.find_one(
        OAuthToken.user_id == user_id,
        OAuthToken.provider == "google"
    )
    if token:
        await token.delete()
    return {"status": "success", "message": "Google Calendar disconnected"}


# ─── Meeting Scheduling ──────────────────────────────────────────────────────

class MeetingCreatePayload(BaseModel):
    summary: str
    description: str
    start_time: datetime
    end_time: datetime


@router.post("/google/events")
async def create_google_event(
    payload: MeetingCreatePayload,
    lead_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    Book a meeting for the current user (team member).
    - Creates a Google Calendar event on the user's calendar.
    - Automatically invites the lead's contact email as an attendee.
    - Logs the meeting in the CRM activity timeline.
    - Advances lead stage to 'meeting' if not already further along.
    """
    # 1. Verify user has Google Calendar connected
    token = await OAuthToken.find_one(
        OAuthToken.user_id == user_id,
        OAuthToken.provider == "google"
    )
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Google Calendar not connected. Please connect your account in Settings > Calendar Integrations."
        )

    # 2. Fetch lead and any associated contact email
    lead = await Lead.find_one(Lead.id == lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    attendees: List[str] = []
    if lead.contact_id:
        contact = await Contact.find_one(Contact.id == lead.contact_id)
        if contact and contact.email:
            attendees.append(contact.email)

    # 3. Create Google Calendar event
    try:
        event = await GoogleCalendarService.create_event(
            user_id=user_id,
            summary=payload.summary,
            description=payload.description,
            start_time=payload.start_time,
            end_time=payload.end_time,
            attendees=attendees
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Calendar error: {str(e)}")

    event_id = event.get("id")

    # 4. Log CRM activity
    activity = CRMActivity(
        lead_id=lead_id,
        user_id=user_id,
        type=ActivityType.MEETING,
        content=f"Meeting scheduled: {payload.summary}",
        metadata={
            "event_id": event_id,
            "google_event_link": event.get("htmlLink"),
            "start": payload.start_time.isoformat(),
            "end": payload.end_time.isoformat(),
            "attendees": attendees,
        }
    )
    await activity.insert()

    # 5. Advance lead stage to 'meeting' if at an earlier stage
    stage_order = [
        CRMLeadStage.LEAD,
        CRMLeadStage.CALL,
        CRMLeadStage.MEETING,
        CRMLeadStage.PROPOSAL,
        CRMLeadStage.NEGOTIATION,
        CRMLeadStage.PROJECT,
        CRMLeadStage.WON,
    ]
    try:
        current_idx = stage_order.index(lead.stage)
        meeting_idx = stage_order.index(CRMLeadStage.MEETING)
        if current_idx < meeting_idx:
            lead.stage = CRMLeadStage.MEETING
            lead.last_activity_at = datetime.utcnow()
            await lead.save()
    except ValueError:
        pass  # If current stage not in order list (e.g., LOST/WON), leave it alone

    return {
        "status": "success",
        "event_id": event_id,
        "google_event_link": event.get("htmlLink"),
        "attendees_invited": attendees
    }
