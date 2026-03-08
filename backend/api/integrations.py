from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
import uuid
from typing import List

from ..services.google_calendar import GoogleCalendarService
from ..api.deps import get_current_user_id
from ..models import OAuthToken
from ..config import settings

router = APIRouter(prefix="/integrations", tags=["integrations"])

@router.get("/google/auth")
async def google_auth(
    redirect_uri: str,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Start Google OAuth flow."""
    flow = GoogleCalendarService.get_flow(redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return {"auth_url": auth_url}

@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str = None,
    redirect_uri: str = Query(...),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Handle Google OAuth callback."""
    try:
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
