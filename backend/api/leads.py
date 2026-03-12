from beanie.operators import In
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime
import re

from ..models import Lead, Contact, ContactList, User, Event, EmailSend, LeadNote, CRMActivity, CRMTask, TaskStatus, ActivityType, Organization, CRMLeadStage, CRMKanbanOrder
from ..schemas.leads import (
    LeadResponse, LeadUpdate, LeadStatsResponse, 
    LeadActivityResponse, LeadActivityItem, LeadCreate,
    TaskResponse, TaskCreate, TaskUpdate, ActivityCreate
)
from ..services.leads import LeadService
from ..services.lead_scoring import LeadScoringService
from ..api.deps import get_current_user_id, get_current_user, ADMIN_ROLES
from ..signals import CRMSignals
from ..cache import cache_get, cache_set, delete_cache

router = APIRouter(prefix="/leads", tags=["leads"])

class LeadStagePatch(BaseModel):
    stage: str

class KanbanOrderPayload(BaseModel):
    stage_order: List[str] = Field(default_factory=list)

class PipelineStageSummary(BaseModel):
    stage: str
    count: int
    deal_value_by_currency: Dict[str, float]

class PipelineSummaryResponse(BaseModel):
    stages: List[PipelineStageSummary]
    totals_by_currency: Dict[str, float]

class LeadProjection(BaseModel):
    id: UUID = Field(alias="_id")
    company_name: str
    source: str
    stage: str
    assigned_to_id: Optional[UUID] = None
    assigned_by_id: Optional[UUID] = None
    lead_status: str
    lead_score: int
    deal_value: float = 0.0
    deal_currency: str = "USD"
    organization_id: Optional[UUID] = None
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime
    claimed_at: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    last_email_opened_at: Optional[datetime] = None
    last_link_clicked_at: Optional[datetime] = None
    is_claimable: bool = False
    assignment_type: Optional[str] = None
    proposal_deadline: Optional[datetime] = None
    deadline_reminder_sent: bool = False

class LeadShortProjection(BaseModel):
    id: UUID = Field(alias="_id")
    company_name: str

class LeadStatsProjection(BaseModel):
    stage: str
    lead_status: str

@router.get("/pipeline-summary", response_model=PipelineSummaryResponse)
async def get_pipeline_summary(
    user_id: UUID = Depends(get_current_user_id),
):
    """Counts + deal totals per stage for Kanban header.

    Previously this pulled every lead into memory and iterated in
    Python.  Replace with a MongoDB aggregation so the database can
    perform the grouping and summing efficiently (indexes will also be
    used).
    """
    # project only the fields we care about ahead of the group stage
    pipeline = [
        {"$project": {"stage": 1, "deal_currency": 1, "deal_value": {"$ifNull": ["$deal_value", 0]}}},
        {"$group": {
            "_id": {"stage": "$stage", "currency": "$deal_currency"},
            "count": {"$sum": 1},
            "deal_value": {"$sum": "$deal_value"}
        }}
    ]

    # ── Cache (60 s) ───────────────────────────────────────────────────────
    cached = await cache_get("leads:pipeline_summary")
    if cached:
        return PipelineSummaryResponse(**cached)
    # ───────────────────────────────────────────────────────────────────────

    raw = await Lead.get_motor_collection().aggregate(pipeline).to_list(length=None)

    stage_map: Dict[str, PipelineStageSummary] = {}
    totals_by_currency: Dict[str, float] = {}

    for entry in raw:
        stage_val = entry["_id"]["stage"]
        cur_val = entry["_id"]["currency"] or "USD"
        cnt = entry.get("count", 0)
        val = float(entry.get("deal_value", 0))

        if stage_val not in stage_map:
            stage_map[stage_val] = PipelineStageSummary(
                stage=stage_val,
                count=0,
                deal_value_by_currency={}
            )
        stage_map[stage_val].count += cnt
        stage_map[stage_val].deal_value_by_currency[cur_val] = (
            stage_map[stage_val].deal_value_by_currency.get(cur_val, 0.0) + val
        )
        totals_by_currency[cur_val] = totals_by_currency.get(cur_val, 0.0) + val

    # stable ordering by CRMLeadStage enum
    order = [s.value for s in CRMLeadStage]
    stages_sorted = sorted(stage_map.values(), key=lambda s: order.index(s.stage) if s.stage in order else 999)

    response = PipelineSummaryResponse(stages=stages_sorted, totals_by_currency=totals_by_currency)
    await cache_set("leads:pipeline_summary", response.model_dump(), ttl=60)
    return response


@router.get("/kanban-order", response_model=KanbanOrderPayload)
async def get_kanban_order(
    user_id: UUID = Depends(get_current_user_id),
):
    """Load per-user Kanban column ordering preferences."""
    pref = await CRMKanbanOrder.find_one(CRMKanbanOrder.user_id == user_id)
    if pref and pref.stage_order:
        return KanbanOrderPayload(stage_order=pref.stage_order)
    return KanbanOrderPayload(stage_order=[s.value for s in CRMLeadStage])


@router.put("/kanban-order", response_model=KanbanOrderPayload)
async def put_kanban_order(
    payload: KanbanOrderPayload,
    user_id: UUID = Depends(get_current_user_id),
):
    """Save per-user Kanban column ordering preferences."""
    valid = {s.value for s in CRMLeadStage}
    deduped: List[str] = []
    for s in payload.stage_order:
        if s in valid and s not in deduped:
            deduped.append(s)

    # append any missing stages so UI never "loses" a column
    for s in [st.value for st in CRMLeadStage]:
        if s not in deduped:
            deduped.append(s)

    pref = await CRMKanbanOrder.find_one(CRMKanbanOrder.user_id == user_id)
    if not pref:
        pref = CRMKanbanOrder(user_id=user_id, stage_order=deduped)
        await pref.insert()
    else:
        pref.stage_order = deduped
        pref.updated_at = datetime.utcnow()
        await pref.save()

    return KanbanOrderPayload(stage_order=deduped)

@router.patch("/{lead_id}/stage", response_model=LeadResponse)
async def patch_lead_stage(
    lead_id: UUID,
    payload: LeadStagePatch,
    user_id: UUID = Depends(get_current_user_id),
):
    """Dedicated stage-change endpoint (logs activity automatically)."""
    lead = await Lead.find_one(Lead.id == lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    try:
        new_stage = CRMLeadStage(payload.stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {payload.stage}")

    updated = await LeadService.update_lead_stage(lead_id, new_stage, user_id)

    details = await LeadService.get_lead_with_details(lead_id)
    assigned_to = details["assigned_to"] if details else None
    assigned_by = details["assigned_by"] if details else None

    lead_data = updated.model_dump()
    lead_data["stage"] = updated.stage.value if hasattr(updated.stage, "value") else updated.stage
    lead_data["lead_status"] = updated.lead_status.value if hasattr(updated.lead_status, "value") else updated.lead_status
    lead_data["assigned_to_name"] = f"{assigned_to.first_name or ''} {assigned_to.last_name or ''}".strip() if assigned_to else None
    lead_data["assigned_to_email"] = assigned_to.email if assigned_to else None
    lead_data["assigned_by_name"] = f"{assigned_by.first_name or ''} {assigned_by.last_name or ''}".strip() if assigned_by else None
    lead_data["assigned_by_email"] = assigned_by.email if assigned_by else None

    # Broadcast update signal
    CRMSignals.broadcast_lead_update(lead_id, user_id, "stage_updated")

    return LeadResponse(**lead_data)

async def _build_lead_responses(leads: List[Lead]) -> List[LeadResponse]:
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
        
        # Build dictionary from model dump
        data = lead.model_dump()
        
        # Ensure ID is included
        data["id"] = lead.id
        
        # Handle Enums/Attributes for LeadResponse
        data["stage"] = lead.stage.value if hasattr(lead.stage, "value") else str(lead.stage)
        data["lead_status"] = lead.lead_status.value if hasattr(lead.lead_status, "value") else str(lead.lead_status)
        data["deal_currency"] = lead.deal_currency.value if hasattr(getattr(lead, "deal_currency", None), "value") else (getattr(lead, "deal_currency", None) or "USD")
        
        # Attach joined user fields
        data["assigned_to_name"] = f"{assigned_to.first_name or ''} {assigned_to.last_name or ''}".strip() if assigned_to else None
        data["assigned_to_email"] = assigned_to.email if assigned_to else None
        data["assigned_by_name"] = f"{assigned_by.first_name or ''} {assigned_by.last_name or ''}".strip() if assigned_by else None
        data["assigned_by_email"] = assigned_by.email if assigned_by else None

        responses.append(LeadResponse(**data))
    
    return responses

# ─── Phase 2: Role-Aware Endpoints ──────────────────────────────────────────

@router.get("/my", response_model=List[LeadResponse])
async def get_my_leads(
    stage: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Returns only leads assigned to the currently logged-in user."""
    query = [Lead.assigned_to_id == current_user.id]
    if stage:
        query.append(Lead.stage == stage)
    if search:
        query.append(Lead.company_name == re.compile(search, re.IGNORECASE))

    leads = await Lead.find(*query).sort("-last_activity_at").project(LeadProjection).to_list()
    return await _build_lead_responses(leads)


@router.get("/pool", response_model=List[LeadResponse])
async def get_lead_pool(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Returns unassigned, claimable leads available in the pool."""
    query = [Lead.is_claimable == True, Lead.assigned_to_id == None]
    if search:
        query.append(Lead.company_name == re.compile(search, re.IGNORECASE))

    leads = await Lead.find(*query).sort("-created_at").project(LeadProjection).to_list()
    return await _build_lead_responses(leads)


@router.post("/{lead_id}/claim", response_model=LeadResponse)
async def claim_lead(
    lead_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Team member claims an unassigned lead from the pool."""
    lead = await Lead.find_one(Lead.id == lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.is_claimable:
        raise HTTPException(status_code=400, detail="This lead is not available in the pool.")
    if lead.assigned_to_id is not None:
        raise HTTPException(status_code=409, detail="This lead has already been claimed by another team member.")

    lead.assigned_to_id = current_user.id
    lead.claimed_by_id = current_user.id
    lead.claimed_at = datetime.utcnow()
    lead.is_claimable = False
    lead.last_activity_at = datetime.utcnow()
    lead.updated_at = datetime.utcnow()
    await lead.save()

    # Log activity
    activity = CRMActivity(
        lead_id=lead_id,
        user_id=current_user.id,
        type=ActivityType.SYSTEM,
        content=f"Lead claimed from pool by {current_user.first_name or current_user.email}",
    )
    try:
        await activity.insert()
    except Exception:
        pass

    leads = await _build_lead_responses([lead])
    
    # Broadcast update signal
    CRMSignals.broadcast_lead_update(lead.id, current_user.id, "claimed")
    
    return leads[0]


@router.get("/tasks/overdue")
async def get_overdue_tasks(
    current_user: User = Depends(get_current_user)
):
    """Fetch overdue tasks for the current user."""
    from ..models import CRMTask, TaskStatus
    from datetime import datetime
    now = datetime.utcnow()
    tasks = await CRMTask.find(
        CRMTask.assigned_to_id == current_user.id,
        CRMTask.status == TaskStatus.PENDING,
        CRMTask.due_date < now
    ).to_list()
    
    # batch load lead names to avoid N+1 query pattern
    lead_ids = list({t.lead_id for t in tasks if t.lead_id})
    leads_map = {}
    if lead_ids:
        leads = await Lead.find(In(Lead.id, lead_ids)).project(LeadShortProjection).to_list()
        leads_map = {l.id: l.company_name for l in leads}

    results = []
    for t in tasks:
        results.append({
            "id": str(t.id),
            "lead_id": str(t.lead_id),
            "company_name": leads_map.get(t.lead_id, "Unknown"),
            "title": t.title,
            "due_date": t.due_date.isoformat() if t.due_date else None
        })
    return results


@router.get("/my/hot")
async def get_hot_leads(
    current_user: User = Depends(get_current_user)
):
    """Fetch leads with score > 70 assigned to current user."""
    leads = await Lead.find(
        Lead.assigned_to_id == current_user.id,
        Lead.lead_score > 70
    ).sort("-lead_score").limit(10).to_list()
    
    return await _build_lead_responses(leads)


@router.get("", response_model=List[LeadResponse])
async def list_leads(
    stage: Optional[str] = None,
    assigned_to_id: Optional[UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user_id: UUID = Depends(get_current_user_id),
    current_user: User = Depends(get_current_user)
):
    """List leads. Team members only see their own leads automatically."""
    query = []

    # Role-based scoping: non-admin roles only see their own leads
    user_role = getattr(current_user, 'role', '') or ''
    if user_role.lower() not in ADMIN_ROLES:
        query.append(Lead.assigned_to_id == current_user.id)

    if stage:
        query.append(Lead.stage == stage)
    if assigned_to_id:
        query.append(Lead.assigned_to_id == assigned_to_id)
    
    if search:
        # Search in company_name
        search_re = re.compile(search, re.IGNORECASE)
        query.append(Lead.company_name == search_re)

    leads = await Lead.find(*query).sort("-created_at").skip(skip).limit(limit).to_list()
    return await _build_lead_responses(leads)

@router.post("", response_model=LeadResponse)
async def create_lead(
    payload: LeadCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new CRM lead with auto-assignment for team members."""
    user_id = current_user.id
    # Link or Create Organization
    org = await Organization.find_one(Organization.name == payload.company_name)
    if not org:
        org = Organization(name=payload.company_name)
        await org.insert()
    
    # Assignment Logic (Phase 6)
    assigned_to_id = payload.assigned_to_id
    assignment_type = "manual" if assigned_to_id else None
    
    if not assigned_to_id and current_user.role == UserRole.TEAM_MEMBER:
        assigned_to_id = current_user.id
        assignment_type = "creator"
    
    lead = Lead(
        company_name=payload.company_name,
        organization_id=org.id,
        source=payload.source.value if hasattr(payload.source, 'value') else payload.source,
        contact_id=payload.contact_id,
        assigned_to_id=assigned_to_id,
        assigned_by_id=user_id if assigned_to_id else None,
        assigned_at=datetime.utcnow() if assigned_to_id else None,
        assignment_type=assignment_type,
        stage=payload.stage or "lead"
    )
    await lead.insert()
    
    # Notifications (Phase 6)
    from ..models import CRMNotification
    if assigned_to_id:
        # 1. Notify the Manager of the assignee/creator
        assignee = await User.find_one(User.id == assigned_to_id)
        if assignee and assignee.manager_id:
            notif = CRMNotification(
                user_id=assignee.manager_id,
                title="New Lead Assigned",
                message=f"Lead '{lead.company_name}' has been assigned to {assignee.first_name or assignee.email}.",
                type="info",
                metadata={"lead_id": str(lead.id)}
            )
            await notif.insert()
    else:
        # 2. Notify all Admins/Managers of a "Fresh Lead" that needs assignment
        admins = await User.find({"role": {"$in": [UserRole.ADMIN, UserRole.MANAGER]}}).to_list()
        for admin in admins:
            notif = CRMNotification(
                user_id=admin.id,
                title="Fresh Lead Needs Assignment",
                message=f"A new unassigned lead '{lead.company_name}' has arrived.",
                type="warning",
                metadata={"lead_id": str(lead.id)}
            )
            await notif.insert()

    # Log initial assignment activity if assigned
    if assigned_to_id:
        from ..services.leads import LeadService
        await LeadService.log_activity(
            lead_id=lead.id,
            user_id=user_id,
            activity_type=ActivityType.SYSTEM,
            content=f"Initial assignment to {current_user.email}" if assignment_type == "creator" else f"Manually assigned to user {assigned_to_id}"
        )
    
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
    # ── Cache (60 s) ───────────────────────────────────────────────────────
    STATS_KEY = "leads:stats"
    cached = await cache_get(STATS_KEY)
    if cached:
        return LeadStatsResponse(**cached)
    # ───────────────────────────────────────────────────────────────────────

    leads = await Lead.find_all().project(LeadStatsProjection).to_list()
    
    stage_counts = {}
    status_counts = {}
    
    for lead in leads:
        st = lead.get("stage")
        ls = lead.get("lead_status")
        stage_val = st.value if hasattr(st, 'value') else st
        status_val = ls.value if hasattr(ls, 'value') else ls
        
        if stage_val:
            stage_counts[stage_val] = stage_counts.get(stage_val, 0) + 1
        if status_val:
            status_counts[status_val] = status_counts.get(status_val, 0) + 1
        
    response = LeadStatsResponse(
        total=len(leads),
        by_stage=stage_counts,
        by_status=status_counts
    )
    await cache_set(STATS_KEY, response.model_dump(), ttl=60)
    return response

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
        CRMSignals.broadcast_lead_update(lead_id, user_id, "assigned")
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
        # Update or create organization
        org = await Organization.find_one(Organization.name == update.company_name)
        if not org:
            org = Organization(name=update.company_name)
            await org.insert()
        lead.organization_id = org.id
    if update.source is not None:
        lead.source = update.source
    if update.lead_status is not None:
        lead.lead_status = update.lead_status
    if update.deal_value is not None:
        lead.deal_value = update.deal_value
    if update.deal_currency is not None:
        lead.deal_currency = update.deal_currency
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
    """Log a manual activity (call, meeting, note, etc.) and auto-update lead score."""
    await LeadService.log_activity(
        lead_id=lead_id,
        user_id=user_id,
        activity_type=ActivityType(activity.type),
        content=activity.content,
        metadata=activity.metadata
    )
    # Auto-score the lead based on this activity
    try:
        await LeadScoringService.score_event(
            lead_id=lead_id,
            event_type=activity.type,
            note=f"Manual {activity.type} logged"
        )
    except Exception:
        pass  # Scoring failure should never block the activity log
        
    CRMSignals.broadcast_activity_update(lead_id, user_id, activity.type)
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
    CRMSignals.broadcast_task_update(lead_id, new_task.id, user_id, "created")
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
    
    CRMSignals.broadcast_activity_update(lead_id, user_id, "note")
    
    return {"message": "Note added"}
