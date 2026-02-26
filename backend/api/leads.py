from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from ..db import get_db
from ..models import Lead, Contact, ContactList, User, Event, EmailSend
from ..schemas.leads import (
    LeadResponse, LeadUpdate, LeadStatsResponse, 
    LeadActivityResponse, LeadActivityItem
)
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/leads", tags=["leads"])

@router.get("", response_model=List[LeadResponse])
async def list_leads(
    contact_list_id: Optional[UUID] = None,
    lead_status: Optional[str] = None,
    assigned_to_id: Optional[UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all leads with filtering and pagination."""
    query = select(
        Lead,
        Contact.email.label("contact_email"),
        Contact.first_name.label("contact_first_name"),
        Contact.last_name.label("contact_last_name"),
        Contact.contact_list_id,
        ContactList.name.label("contact_list_name"),
        User.email.label("assigned_to_email"),
        User.first_name.label("assigned_to_first_name"),
        User.last_name.label("assigned_to_last_name")
    ).join(
        Contact, Lead.contact_id == Contact.id
    ).join(
        ContactList, Contact.contact_list_id == ContactList.id
    ).outerjoin(
        User, Lead.assigned_to_id == User.id
    )
    
    # Apply filters
    if contact_list_id:
        query = query.where(Contact.contact_list_id == contact_list_id)
    if lead_status:
        query = query.where(Lead.lead_status == lead_status)
    if assigned_to_id:
        query = query.where(Lead.assigned_to_id == assigned_to_id)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Contact.email.ilike(search_pattern),
                Contact.first_name.ilike(search_pattern),
                Contact.last_name.ilike(search_pattern)
            )
        )
    
    # Order by created_at desc
    query = query.order_by(Lead.created_at.desc())
    
    # Pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Transform to response model
    leads = []
    for row in rows:
        lead_dict = {
            "id": row.Lead.id,
            "contact_id": row.Lead.contact_id,
            "lead_status": row.Lead.lead_status.value,
            "lead_score": row.Lead.lead_score,
            "assigned_to_id": row.Lead.assigned_to_id,
            "claimed_at": row.Lead.claimed_at,
            "last_contacted_at": row.Lead.last_contacted_at,
            "last_email_opened_at": row.Lead.last_email_opened_at,
            "last_link_clicked_at": row.Lead.last_link_clicked_at,
            "created_at": row.Lead.created_at,
            "updated_at": row.Lead.updated_at,
            "contact_email": row.contact_email,
            "contact_first_name": row.contact_first_name,
            "contact_last_name": row.contact_last_name,
            "contact_list_id": row.contact_list_id,
            "contact_list_name": row.contact_list_name,
            "assigned_to_email": row.assigned_to_email,
            "assigned_to_name": f"{row.assigned_to_first_name or ''} {row.assigned_to_last_name or ''}".strip() if row.assigned_to_first_name or row.assigned_to_last_name else None
        }
        leads.append(LeadResponse(**lead_dict))
    
    return leads

@router.get("/stats", response_model=LeadStatsResponse)
async def get_lead_stats(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get lead statistics."""
    # Total count
    total_query = select(func.count()).select_from(Lead)
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()
    
    # Count by status
    status_query = select(
        Lead.lead_status,
        func.count().label("count")
    ).group_by(Lead.lead_status)
    status_result = await db.execute(status_query)
    status_counts = {row.lead_status.value: row.count for row in status_result}
    
    # Count by list
    list_query = select(
        ContactList.name,
        func.count(Lead.id).label("count")
    ).join(
        Contact, Contact.contact_list_id == ContactList.id
    ).join(
        Lead, Lead.contact_id == Contact.id
    ).group_by(ContactList.name)
    list_result = await db.execute(list_query)
    by_list = {row.name: row.count for row in list_result}
    
    return LeadStatsResponse(
        total=total,
        new=status_counts.get("new", 0),
        warm=status_counts.get("warm", 0),
        hot=status_counts.get("hot", 0),
        cold=status_counts.get("cold", 0),
        unsubscribed=status_counts.get("unsubscribed", 0),
        by_list=by_list
    )

@router.get("/by-list/{list_id}", response_model=List[LeadResponse])
async def get_leads_by_list(
    list_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get all leads from a specific contact list."""
    return await list_leads(contact_list_id=list_id, db=db, user_id=user_id)

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get a single lead by ID."""
    query = select(
        Lead,
        Contact.email.label("contact_email"),
        Contact.first_name.label("contact_first_name"),
        Contact.last_name.label("contact_last_name"),
        Contact.contact_list_id,
        ContactList.name.label("contact_list_name"),
        User.email.label("assigned_to_email"),
        User.first_name.label("assigned_to_first_name"),
        User.last_name.label("assigned_to_last_name")
    ).join(
        Contact, Lead.contact_id == Contact.id
    ).join(
        ContactList, Contact.contact_list_id == ContactList.id
    ).outerjoin(
        User, Lead.assigned_to_id == User.id
    ).where(Lead.id == lead_id)
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead_dict = {
        "id": row.Lead.id,
        "contact_id": row.Lead.contact_id,
        "lead_status": row.Lead.lead_status.value,
        "lead_score": row.Lead.lead_score,
        "assigned_to_id": row.Lead.assigned_to_id,
        "claimed_at": row.Lead.claimed_at,
        "last_contacted_at": row.Lead.last_contacted_at,
        "last_email_opened_at": row.Lead.last_email_opened_at,
        "last_link_clicked_at": row.Lead.last_link_clicked_at,
        "created_at": row.Lead.created_at,
        "updated_at": row.Lead.updated_at,
        "contact_email": row.contact_email,
        "contact_first_name": row.contact_first_name,
        "contact_last_name": row.contact_last_name,
        "contact_list_id": row.contact_list_id,
        "contact_list_name": row.contact_list_name,
        "assigned_to_email": row.assigned_to_email,
        "assigned_to_name": f"{row.assigned_to_first_name or ''} {row.assigned_to_last_name or ''}".strip() if row.assigned_to_first_name or row.assigned_to_last_name else None
    }
    
    return LeadResponse(**lead_dict)

@router.post("/{lead_id}/assign")
async def assign_lead(
    lead_id: UUID,
    assigned_to_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Assign a lead to a user."""
    query = select(Lead).where(Lead.id == lead_id)
    result = await db.execute(query)
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.assigned_to_id = assigned_to_id
    lead.claimed_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Lead assigned successfully"}

@router.patch("/{lead_id}")
async def update_lead(
    lead_id: UUID,
    update: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Consolidated endpoint to update lead and contact details."""
    # Fetch lead and contact together
    query = select(Lead, Contact).join(Contact, Lead.contact_id == Contact.id).where(Lead.id == lead_id)
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    lead, contact = row
    
    # 1. Update Lead Fields
    if update.lead_status is not None:
        old_status = lead.lead_status.value
        if old_status != update.lead_status:
            lead.lead_status = update.lead_status
            # Log system note for status change
            from ..models import LeadNote
            note = LeadNote(
                lead_id=lead_id,
                user_id=user_id,
                content=f"Status changed from {old_status} to {update.lead_status}",
                is_system=True
            )
            db.add(note)
            
    if update.lead_score is not None:
        lead.lead_score = update.lead_score
        
    if update.assigned_to_id is not None:
        lead.assigned_to_id = update.assigned_to_id
        lead.claimed_at = datetime.utcnow()
        
    if update.last_contacted_at is not None:
        lead.last_contacted_at = update.last_contacted_at

    # 2. Update Contact Fields
    if update.email is not None:
        contact.email = update.email
    if update.first_name is not None:
        contact.first_name = update.first_name
    if update.last_name is not None:
        contact.last_name = update.last_name
    if update.contact_list_id is not None:
        contact.contact_list_id = update.contact_list_id
    if update.attributes is not None:
        # Merge attributes
        current_attrs = contact.attributes or {}
        current_attrs.update(update.attributes)
        contact.attributes = current_attrs
    
    await db.commit()
    return {"message": "Lead updated successfully"}

@router.get("/{lead_id}/activity", response_model=LeadActivityResponse)
async def get_lead_activity(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get activity timeline for a lead."""
    # Get the lead and contact
    lead_query = select(Lead, Contact).join(Contact, Lead.contact_id == Contact.id).where(Lead.id == lead_id)
    lead_result = await db.execute(lead_query)
    lead_row = lead_result.first()
    
    if not lead_row:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead, contact = lead_row
    
    # Get events for this contact's email by joining with EmailSend
    events_query = select(Event, EmailSend).join(
        EmailSend, Event.email_send_id == EmailSend.id
    ).where(
        EmailSend.to_email == contact.email
    ).order_by(Event.created_at.desc()).limit(50)
    
    events_result = await db.execute(events_query)
    events = events_result.all()

    # Get notes
    from ..models import LeadNote
    notes_query = select(LeadNote, User).outerjoin(User, LeadNote.user_id == User.id).where(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc())
    notes_result = await db.execute(notes_query)
    notes = notes_result.all()
    
    activities = []
    
    # Add "Joined System"
    activities.append(LeadActivityItem(
        id=lead.id,
        type="system",
        description="Joined System",
        created_at=lead.created_at,
        source="System"
    ))

    # Add Events
    for event, email_send in events:
        activities.append(LeadActivityItem(
            id=event.id,
            type=event.type,
            description=f"Email {event.type}",
            created_at=event.created_at,
            metadata={"campaign_id": str(email_send.campaign_id) if email_send.campaign_id else None},
            source="Email System"
        ))

    # Add Notes & System Logs
    for note, user in notes:
        activities.append(LeadActivityItem(
            id=note.id,
            type="note" if not note.is_system else "system",
            description=note.content,
            created_at=note.created_at,
            source=f"{user.first_name} {user.last_name}" if user else "System"
        ))
    
    # Sort by created_at desc
    activities.sort(key=lambda x: x.created_at, reverse=True)
    
    return LeadActivityResponse(lead_id=lead_id, activities=activities)


@router.post("/{lead_id}/notes")
async def create_lead_note(
    lead_id: UUID,
    note: dict, # {content: str}
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Add a note to a lead."""
    from ..models import LeadNote
    
    content = note.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Content required")

    new_note = LeadNote(
        lead_id=lead_id,
        user_id=user_id,
        content=content,
        is_system=False
    )
    db.add(new_note)
    await db.commit()
    return {"message": "Note added"}
