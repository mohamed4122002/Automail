import os
import json
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import uuid

from ..models import OAuthToken, CRMActivity, ActivityType
from ..config import settings
from ..core.retries import with_retry

class GoogleCalendarService:
    SCOPES = ['https://www.googleapis.com/auth/calendar.events']
    
    @staticmethod
    def get_flow(redirect_uri: str):
        """Create a Google OAuth2 flow instance."""
        client_config = {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        return Flow.from_client_config(
            client_config,
            scopes=GoogleCalendarService.SCOPES,
            redirect_uri=redirect_uri
        )

    @staticmethod
    async def save_token(user_id: uuid.UUID, credentials):
        """Save or update OAuth token for a user."""
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else []
        }
        
        token_doc = await OAuthToken.find_one(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "google"
        )
        
        if token_doc:
            token_doc.token_data = token_data
            token_doc.scopes = token_data["scopes"]
            token_doc.updated_at = datetime.utcnow()
            await token_doc.save()
        else:
            token_doc = OAuthToken(
                user_id=user_id,
                provider="google",
                token_data=token_data,
                scopes=token_data["scopes"]
            )
            await token_doc.insert()
            
        return token_doc

    @staticmethod
    async def get_calendar_client(user_id: uuid.UUID):
        """
        Get an authorized Google Calendar API client.
        Automatically refreshes the access token if it has expired.
        """
        token_doc = await OAuthToken.find_one(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "google"
        )
        
        if not token_doc:
            return None
        
        td = token_doc.token_data
        creds = Credentials(
            token=td.get("token"),
            refresh_token=td.get("refresh_token"),
            token_uri=td.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=td.get("client_id"),
            client_secret=td.get("client_secret"),
            scopes=td.get("scopes"),
        )
        
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleAuthRequest())
            # Persist the refreshed token
            token_doc.token_data["token"] = creds.token
            token_doc.updated_at = datetime.utcnow()
            await token_doc.save()
        
        service = build('calendar', 'v3', credentials=creds)
        return service

    @staticmethod
    @with_retry(max_attempts=3)
    async def create_event(
        user_id: uuid.UUID,
        summary: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str] = None
    ):
        """Create a calendar event."""
        service = await GoogleCalendarService.get_calendar_client(user_id)
        if not service:
            raise Exception("Google Calendar not connected for this user.")
            
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [{'email': email} for email in attendees] if attendees else [],
            'reminders': {
                'useDefault': True,
            },
        }
        
        event = service.events().insert(
            calendarId='primary', 
            body=event,
            sendUpdates='all'
        ).execute()
        return event
