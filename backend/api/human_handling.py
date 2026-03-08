from beanie.operators import In
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
import io
import csv

from ..models import User, Event, EventTypeEnum, Contact, Lead, LeadStatusEnum
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/human-handling-list")
async def get_human_handling_list(
    days: int = Query(30, description="Look back period in days"),
    owner_id: UUID = Depends(get_current_user_id)
):
    """
    Get list of users who opened emails but didn't click links.
    These users need human follow-up (Path 2 from vision).
    """
    
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get all users who opened emails
    opened_events = await Event.find(
        Event.type == EventTypeEnum.OPENED,
        Event.created_at >= since
    ).to_list()
    
    opened_user_ids = {e.user_id for e in opened_events if e.user_id}
    
    # Get all users who clicked emails
    clicked_events = await Event.find(
        Event.type == EventTypeEnum.CLICKED,
        Event.created_at >= since
    ).to_list()
    
    clicked_user_ids = {e.user_id for e in clicked_events if e.user_id}
    
    # Users who opened but didn't click
    target_user_ids = list(opened_user_ids - clicked_user_ids)
    
    if not target_user_ids:
        return {
            "total": 0,
            "users": [],
            "period_days": days
        }
    
    users = await User.find(In(User.id, target_user_ids)).to_list()
    
    user_list = []
    for user in users:
        # Get last opened event
        last_open_events = await Event.find(
            Event.user_id == user.id,
            Event.type == EventTypeEnum.OPENED,
            Event.created_at >= since
        ).sort("-created_at").limit(1).to_list()
        
        if last_open_events:
            last_open = last_open_events[0]
            days_since_open = (datetime.utcnow() - last_open.created_at).days
            
            # Fetch lead status
            lead_status_str = "unknown"
            contact = await Contact.find_one(Contact.email == user.email)
            if contact:
                lead = await Lead.find_one(Lead.contact_id == contact.id)
                if lead:
                    lead_status_str = lead.lead_status.value if hasattr(lead.lead_status, 'value') else str(lead.lead_status)
            
            user_list.append({
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "last_email_opened": last_open.created_at.isoformat(),
                "days_since_open": days_since_open,
                "lead_status": lead_status_str,
                "contacted": lead_status_str == "contacted"
            })
    
    # Sort by days since open (most recent first)
    user_list.sort(key=lambda x: x["days_since_open"])
    
    return {
        "total": len(user_list),
        "users": user_list,
        "period_days": days
    }


@router.post("/human-handling-list/export")
async def export_human_handling_list(
    days: int = Query(30, description="Look back period in days"),
    owner_id: UUID = Depends(get_current_user_id)
):
    """
    Export human handling list to CSV for sales team.
    """
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get all users who opened emails
    opened_events = await Event.find(
        Event.type == EventTypeEnum.OPENED,
        Event.created_at >= since
    ).to_list()
    
    opened_user_ids = {e.user_id for e in opened_events if e.user_id}
    
    # Get all users who clicked emails
    clicked_events = await Event.find(
        Event.type == EventTypeEnum.CLICKED,
        Event.created_at >= since
    ).to_list()
    
    clicked_user_ids = {e.user_id for e in clicked_events if e.user_id}
    
    # Users who opened but didn't click
    target_user_ids = list(opened_user_ids - clicked_user_ids)
    
    users = []
    if target_user_ids:
        users = await User.find(In(User.id, target_user_ids)).to_list()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Email',
        'First Name',
        'Last Name',
        'Last Email Opened',
        'Days Since Open',
        'Lead Status'
    ])
    
    # Write data
    for user in users:
        last_open_events = await Event.find(
            Event.user_id == user.id,
            Event.type == EventTypeEnum.OPENED,
            Event.created_at >= since
        ).sort("-created_at").limit(1).to_list()
        
        if last_open_events:
            last_open = last_open_events[0]
            days_since_open = (datetime.utcnow() - last_open.created_at).days
            
            lead_status_str = "unknown"
            contact = await Contact.find_one(Contact.email == user.email)
            if contact:
                lead = await Lead.find_one(Lead.contact_id == contact.id)
                if lead:
                    lead_status_str = lead.lead_status.value if hasattr(lead.lead_status, 'value') else str(lead.lead_status)
            
            writer.writerow([
                user.email,
                user.first_name or '',
                user.last_name or '',
                last_open.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                days_since_open,
                lead_status_str
            ])
    
    # Return CSV file
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=human_handling_list_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        }
    )


@router.post("/{user_id}/mark-contacted")
async def mark_user_as_contacted(
    user_id: UUID,
    owner_id: UUID = Depends(get_current_user_id)
):
    """
    Mark a user as contacted by sales team.
    Updates lead_status to 'contacted' (warm if we don't have contacted enum yet, maybe hot?).
    We'll set `lead_status` directly.
    """
    
    user = await User.find_one(User.id == user_id)
    
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
        
    contact = await Contact.find_one(Contact.email == user.email)
    if not contact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Contact not found")
        
    lead = await Lead.find_one(Lead.contact_id == contact.id)
    if not lead:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.lead_status = "warm" # Assuming 'contacted' is handled as 'warm' or similar in LeadStatusEnum
    lead.updated_at = datetime.utcnow()
    await lead.save()
    
    return {
        "message": "User marked as contacted (warm)",
        "user_id": str(user_id),
        "lead_status": "warm"
    }
