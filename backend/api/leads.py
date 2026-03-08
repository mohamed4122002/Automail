from beanie.operators import In
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import re

from ..models import Lead, Contact, ContactList, User, Event, EmailSend, LeadNote, CRMActivity, CRMTask, TaskStatus, ActivityType
from ..schemas.leads import (
    LeadResponse, LeadUpdate, LeadStatsResponse, 
    LeadActivityResponse, LeadActivityItem, LeadCreate,
    TaskResponse, TaskCreate, TaskUpdate, ActivityCreate
)
from ..services.leads import LeadService
from ..api.deps import get_current_user_id
from ..signals import CRMSignals

router = APIRouter(prefix="/leads", tags=["leads"])

@router.get("", response_model=List[LeadResponse])
async def list_leads(
    stage: Optional[str] = None,
    assigned_to_id: Optional[UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user_id: UUID = Depends(get_current_user_id)
):
    """List all leads with filtering and pagination for CRM."""
    query = []
    if stage:
        query.append(Lead.stage == stage)
    if assigned_to_id:
        query.append(Lead.assigned_to_id == assigned_to_id)
    
    if search:
        # Search in company_name
        search_re = re.compile(search, re.IGNORECASE)
        query.append(Lead.company_name == search_re)

    leads = await Lead.find(*query).sort("-created_at").skip(skip).limit(limit).to_list()
    
    if not leads:
        return []
    
    # Batch fetch users for assignment info
    assigned_ids = list(set([l.assigned_to_id for l in leads if l.assigned_to_id]))
    assigner_ids = list(set([l.assigned_by_id for l in leads if l.assigned_by_id]))
    all_user_ids = list(set(assigned_ids + assigner_ids))
    
    users_map = {u.id: u for u in await User.find(In(User.id, all_user_ids)).to_list()} if all_user_ids else {}

    responses = []
    for lead in leads:
        assigned_to = users_map.get(lead.assigned_to_id)
        assigned_by = users_map.get(lead.assigned_by_id)
        
        responses.append(LeadResponse(
            id=lead.id,
            company_name=lead.company_name,
            source=lead.source,
            stage=lead.stage.value if hasattr(lead.stage, 'value') else lead.stage,
            assigned_to_id=lead.assigned_to_id,
            assigned_by_id=lead.assigned_by_id,
            proposal_deadline=lead.proposal_deadline,
            last_activity_at=lead.last_activity_at,
            lead_status=lead.lead_status.value if hasattr(lead.lead_status, 'value') else lead.lead_status,
            lead_score=lead.lead_score,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
            assigned_to_name=f"{assigned_to.first_name or ''} {assigned_to.last_name or ''}".strip() if assigned_to else None,
            assigned_to_email=assigned_to.email if assigned_to else None,
            assigned_by_name=f"{assigned_by.first_name or ''} {assigned_by.last_name or ''}".strip() if assigned_by else None,
            assigned_by_email=assigned_by.email if assigned_by else None
        ))
    
    return responses

@router.post("", response_model=LeadResponse)
async def create_lead(
    payload: LeadCreate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new CRM lead."""
    lead = Lead(
        company_name=payload.company_name,
        source=payload.source,
        contact_id=payload.contact_id,
        assigned_to_id=payload.assigned_to_id,
        assigned_by_id=user_id if payload.assigned_to_id else None,
        stage=payload.stage or "lead"
    )
    await lead.insert()
    
    # Broadcast signal
    CRMSignals.broadcast_lead_update(lead.id, user_id, "created")
    
    # Fetch details for response
    from ..services.leads import LeadService
    details = await LeadService.get_lead_with_details(lead.id)
    
    return LeadResponse(
        **lead.model_dump(),
        id=lead.id,
        assigned_to_name=f"{details['assigned_to'].first_name or ''} {details['assigned_to'].last_name or ''}".strip() if details and details['assigned_to'] else None,
        assigned_to_email=details['assigned_to'].email if details and details['assigned_to'] else None
    )

@router.get("/stats", response_model=LeadStatsResponse)
async def get_lead_stats(
    user_id: UUID = Depends(get_current_user_id)
):
    """Get lead statistics for CRM and Marketing."""
    leads = await Lead.find_all().to_list()
    
    stage_counts = {}
    status_counts = {}
    
    for lead in leads:
        stage_val = lead.stage.value if hasattr(lead.stage, 'value') else lead.stage
        status_val = lead.lead_status.value if hasattr(lead.lead_status, 'value') else lead.lead_status
        
        stage_counts[stage_val] = stage_counts.get(stage_val, 0) + 1
        status_counts[status_val] = status_counts.get(status_val, 0) + 1
        
    return LeadStatsResponse(
        total=len(leads),
        by_stage=stage_counts,
        by_status=status_counts
    )

@router.get("/by-list/{list_id}", response_model=List[LeadResponse])
async def get_leads_by_list(
    list_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get all leads from a specific contact list."""
    return await list_leads(contact_list_id=list_id, user_id=user_id)

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get a single lead by ID with CRM details."""
    from ..services.leads import LeadService
    details = await LeadService.get_lead_with_details(lead_id)
    if not details:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    lead = details["lead"]
    assigned_to = details["assigned_to"]
    assigned_by = details["assigned_by"]
    
    lead_data = lead.model_dump()
    # Override enum fields with their string values (safe even if already str)
    lead_data['stage'] = lead.stage.value if hasattr(lead.stage, 'value') else lead.stage
    lead_data['lead_status'] = lead.lead_status.value if hasattr(lead.lead_status, 'value') else lead.lead_status
    # Attach joined user fields
    lead_data['assigned_to_name'] = f"{assigned_to.first_name or ''} {assigned_to.last_name or ''}".strip() if assigned_to else None
    lead_data['assigned_to_email'] = assigned_to.email if assigned_to else None
    lead_data['assigned_by_name'] = f"{assigned_by.first_name or ''} {assigned_by.last_name or ''}".strip() if assigned_by else None
    lead_data['assigned_by_email'] = assigned_by.email if assigned_by else None

    return LeadResponse(**lead_data)

@router.post("/{lead_id}/assign")
async def assign_lead(
    lead_id: UUID,
    assigned_to_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Assign a lead to a user using LeadService."""
    from ..services.leads import LeadService
    try:
        await LeadService.assign_lead(lead_id, assigned_to_id, user_id)
        return {"message": "Lead assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{lead_id}")
async def update_lead(
    lead_id: UUID,
    update: LeadUpdate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Update lead details, including stage transitions."""
    from ..services.leads import LeadService
    lead = await Lead.find_one(Lead.id == lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # 1. Update Basic CRM/Marketing Fields
    if update.company_name is not None:
        lead.company_name = update.company_name
    if update.source is not None:
        lead.source = update.source
    if update.lead_status is not None:
        lead.lead_status = update.lead_status
    if update.lead_score is not None:
        lead.lead_score = update.lead_score
    if update.deal_value is not None:
        lead.deal_value = update.deal_value
    if update.proposal_deadline is not None:
        lead.proposal_deadline = update.proposal_deadline
        
    lead.updated_at = datetime.utcnow()
    lead.last_activity_at = datetime.utcnow()
    await lead.save()

    # 2. Handle CRM Stage Transition (Done after save to avoid overwriting stage)
    if update.stage is not None and lead.stage != update.stage:
        try:
            from ..models import CRMLeadStage
            new_stage = CRMLeadStage(update.stage)
            await LeadService.update_lead_stage(lead_id, new_stage, user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {update.stage}")

    # 3. Handle Assignment if provided in update
    if update.assigned_to_id is not None:
        await LeadService.assign_lead(lead_id, update.assigned_to_id, user_id)
            
    # Broadcast update signal
    CRMSignals.broadcast_lead_update(lead_id, user_id, "updated")
            
    # Trigger instant dashboard recalculation
    try:
        from ..tasks import sync_dashboard_metrics
        sync_dashboard_metrics.delay()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to submit dashboard metrics sync task: {e}")

    return {"message": "Lead updated successfully"}

@router.get("/{lead_id}/activity", response_model=LeadActivityResponse)
async def get_lead_activity(
    lead_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get activity timeline for a lead."""
    lead = await Lead.find_one(Lead.id == lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    contact = await Contact.find_one(Contact.id == lead.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Get events for this contact's email by joining with EmailSend (in memory or querying sequentially)
    # First, find sends to this contact's email
    # Let's assume EmailSend's `to_email` isn't fully robust, relying on `user_id` is better if they correspond to shadow users
    shadow_user = await User.find_one(User.email == contact.email)
    
    activities = []
    
    # Add "Joined System"
    activities.append(LeadActivityItem(
        id=lead.id,
        type="system",
        description="Joined System",
        created_at=lead.created_at,
        source="System"
    ))
    
    if shadow_user:
        # Get emails and events
        sends = await EmailSend.find(EmailSend.user_id == shadow_user.id).to_list()
        send_map = {s.id: s for s in sends}
        
        events = await Event.find(Event.user_id == shadow_user.id).sort("-created_at").limit(50).to_list()
        for event in events:
            email_send = send_map.get(event.email_send_id)
            activities.append(LeadActivityItem(
                id=event.id,
                type=event.type,
                description=f"Email {event.type}",
                created_at=event.created_at,
                metadata={"campaign_id": str(email_send.campaign_id) if email_send and email_send.campaign_id else None},
                source="Email System"
            ))

    # Get legacy notes (keeping for compatibility)
    notes = await LeadNote.find(LeadNote.lead_id == lead_id).sort("-created_at").to_list()
    # fetch users for notes
    note_user_ids = list(set([n.user_id for n in notes if n.user_id]))
    users_for_notes = {u.id: u.first_name + " " + (u.last_name or "") for u in await User.find(In(User.id, note_user_ids)).to_list()}

    for note in notes:
        user_name = users_for_notes.get(note.user_id, "System") if note.user_id else "System"
        activities.append(LeadActivityItem(
            id=note.id,
            type="note" if not note.is_system else "system",
            description=note.content,
            created_at=note.created_at,
            source=user_name if not note.is_system else "System"
        ))

    # Get CRM Activities (New)
    crm_activities = await CRMActivity.find(CRMActivity.lead_id == lead_id).sort("-created_at").to_list()
    crm_user_ids = list(set([a.user_id for a in crm_activities if a.user_id]))
    users_for_crm = {u.id: u.first_name + " " + (u.last_name or "") for u in await User.find(In(User.id, crm_user_ids)).to_list()}

    for activity in crm_activities:
        user_name = users_for_crm.get(activity.user_id, "System") if activity.user_id else "System"
        activities.append(LeadActivityItem(
            id=activity.id,
            type=activity.type,
            description=activity.content,
            created_at=activity.created_at,
            metadata=activity.metadata,
            source=user_name
        ))
    
    # Sort by created_at desc
    activities.sort(key=lambda x: x.created_at, reverse=True)
    
    return LeadActivityResponse(lead_id=lead_id, activities=activities)


@router.post("/{lead_id}/activities")
async def log_lead_activity(
    lead_id: UUID,
    activity: ActivityCreate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Log a manual activity (call, meeting, etc.)"""
    await LeadService.log_activity(
        lead_id=lead_id,
        user_id=user_id,
        activity_type=ActivityType(activity.type),
        content=activity.content,
        metadata=activity.metadata
    )
    return {"message": "Activity logged"}

# Task Management
@router.get("/{lead_id}/tasks", response_model=List[TaskResponse])
async def list_lead_tasks(
    lead_id: UUID,
    status: Optional[str] = None,
    user_id: UUID = Depends(get_current_user_id)
):
    """List tasks for a lead."""
    task_status = TaskStatus(status) if status else None
    tasks = await LeadService.get_tasks(lead_id, task_status)
    return tasks

@router.post("/{lead_id}/tasks", response_model=TaskResponse)
async def create_lead_task(
    lead_id: UUID,
    task: TaskCreate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a follow-up task."""
    new_task = await LeadService.create_task(
        lead_id=lead_id,
        assigned_to_id=task.assigned_to_id or user_id,
        title=task.title,
        description=task.description,
        due_date=task.due_date
    )
    return new_task

@router.patch("/{lead_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_lead_task(
    lead_id: UUID,
    task_id: UUID,
    update: TaskUpdate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Update task status (Complete/Cancel)."""
    updated_task = await LeadService.update_task_status(
        task_id=task_id,
        status=TaskStatus(update.status),
        user_id=user_id
    )
    return updated_task


@router.post("/{lead_id}/notes")
async def create_lead_note(
    lead_id: UUID,
    note: dict, # {content: str}
    user_id: UUID = Depends(get_current_user_id)
):
    """Add a note to a lead."""
    content = note.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Content required")

    new_note = LeadNote(
        lead_id=lead_id,
        user_id=user_id,
        content=content,
        is_system=False
    )
    await new_note.insert()
    
    return {"message": "Note added"}
