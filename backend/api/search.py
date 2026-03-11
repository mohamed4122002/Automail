from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Union
import uuid
from ..api.deps import get_current_user_id
from ..models import Lead, Contact, Organization

router = APIRouter(prefix="/search", tags=["search"])

class SearchResult(BaseModel):
    id: uuid.UUID
    type: str # 'lead', 'contact', 'organization'
    title: str
    subtitle: Optional[str] = None
    link: str

@router.get("", response_model=List[SearchResult])
async def global_search(
    q: str = Query(..., min_length=2),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    Perform a unified full-text search across Leads, Contacts, and Organizations.
    """
    results = []

    # 1. Search Leads
    leads = await Lead.find({"$text": {"$search": q}}).limit(5).to_list()
    for l in leads:
        results.append(SearchResult(
            id=l.id,
            type="lead",
            title=l.company_name,
            subtitle=f"Stage: {l.stage}",
            link=f"/leads/{l.id}"
        ))

    # 2. Search Contacts
    contacts = await Contact.find({"$text": {"$search": q}}).limit(5).to_list()
    for c in contacts:
        results.append(SearchResult(
            id=c.id,
            type="contact",
            title=f"{c.first_name or ''} {c.last_name or ''}".strip() or c.email,
            subtitle=c.email,
            link=f"/contacts/{c.id}"
        ))

    # 3. Search Organizations
    orgs = await Organization.find({"$text": {"$search": q}}).limit(5).to_list()
    for o in orgs:
        results.append(SearchResult(
            id=o.id,
            type="organization",
            title=o.name,
            subtitle=o.industry or "Industry TBD",
            link=f"/organizations/{o.id}"
        ))

    return results
