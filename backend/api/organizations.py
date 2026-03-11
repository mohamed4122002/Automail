from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import List, Optional
from ..models import Organization, Lead, User
from ..schemas.organizations import OrganizationResponse, OrganizationCreate, OrganizationUpdate
from ..schemas.leads import LeadResponse
from ..api.deps import get_current_user_id
from beanie.operators import In
import re

router = APIRouter(prefix="/organizations", tags=["organizations"])

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user_id: UUID = Depends(get_current_user_id)
):
    """List all organizations with search and pagination."""
    query = []
    if search:
        search_re = re.compile(search, re.IGNORECASE)
        query.append(Organization.name == search_re)
    
    organizations = await Organization.find(*query).sort("-created_at").skip(skip).limit(limit).to_list()
    return organizations

@router.post("", response_model=OrganizationResponse)
async def create_organization(
    payload: OrganizationCreate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new organization."""
    # Check if exists
    existing = await Organization.find_one(Organization.name == payload.name)
    if existing:
        raise HTTPException(status_code=400, detail="Organization already exists")
        
    org = Organization(**payload.model_dump())
    await org.insert()
    return org

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get organization by ID."""
    org = await Organization.find_one(Organization.id == org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    payload: OrganizationUpdate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Update organization details."""
    org = await Organization.find_one(Organization.id == org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    
    await org.save()
    return org

@router.get("/{org_id}/leads", response_model=List[LeadResponse])
async def list_organization_leads(
    org_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """List all leads belonging to an organization."""
    leads = await Lead.find(Lead.organization_id == org_id).sort("-created_at").to_list()
    
    if not leads:
        return []
        
    # Standard enrichment logic as found in leads.py
    assigned_ids = list(set([l.assigned_to_id for l in leads if l.assigned_to_id]))
    assigner_ids = list(set([l.assigned_by_id for l in leads if l.assigned_by_id]))
    all_user_ids = list(set(assigned_ids + assigner_ids))
    
    users_map = {u.id: u for u in await User.find(In(User.id, all_user_ids)).to_list()} if all_user_ids else {}

    responses = []
    for lead in leads:
        assigned_to = users_map.get(lead.assigned_to_id)
        assigned_by = users_map.get(lead.assigned_by_id)
        
        responses.append(LeadResponse(
            **lead.model_dump(),
            id=lead.id,
            stage=lead.stage.value if hasattr(lead.stage, 'value') else lead.stage,
            lead_status=lead.lead_status.value if hasattr(lead.lead_status, 'value') else lead.lead_status,
            assigned_to_name=f"{assigned_to.first_name or ''} {assigned_to.last_name or ''}".strip() if assigned_to else None,
            assigned_to_email=assigned_to.email if assigned_to else None,
            assigned_by_name=f"{assigned_by.first_name or ''} {assigned_by.last_name or ''}".strip() if assigned_by else None,
            assigned_by_email=assigned_by.email if assigned_by else None
        ))
    
    return responses
