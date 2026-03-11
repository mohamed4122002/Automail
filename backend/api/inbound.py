from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

from ..models import Lead, Contact, CRMActivity, ActivityType, CRMLeadStage, CRMInboundEmail, User
from ..services.leads import LeadService
from .deps import get_current_user_id

router = APIRouter(prefix="/inbound", tags=["inbound"])

class FormSubmission(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None
    source: str = "Web Form"
    metadata: Dict[str, Any] = {}

@router.post("/form")
async def handle_form_submission(submission: FormSubmission):
    """
    Handle inbound form submissions from external websites.
    Links to existing leads or creates new ones.
    """
    # 1. Find or create contact
    contact = await Contact.find_one(Contact.email == submission.email)
    if not contact:
        contact = Contact(
            email=submission.email,
            first_name=submission.first_name,
            last_name=submission.last_name,
            company=submission.company
        )
        await contact.insert()
    
    # 2. Find or create lead
    lead = await Lead.find_one(Lead.contact_id == contact.id)
    if not lead:
        lead = Lead(
            contact_id=contact.id,
            company_name=submission.company or "Inbound Lead",
            source=submission.source,
            stage=CRMLeadStage.LEAD
        )
        await lead.insert()
    
    # 3. Create 'FORM' activity
    content = f"Form Submission: {submission.message}" if submission.message else "Inbound form submission received."
    activity = CRMActivity(
        lead_id=lead.id,
        type=ActivityType.FORM,
        content=content,
        metadata={
            "form_data": submission.model_dump(),
            "received_at": datetime.utcnow().isoformat()
        }
    )
    await activity.insert()
    
    # 4. Update lead last activity
    lead.last_activity_at = datetime.utcnow()
    await lead.save()
    
    # Note: We could trigger a notification here too
    
    return {"status": "success", "lead_id": str(lead.id)}


class InboundEmailPayload(BaseModel):
    from_email: EmailStr
    subject: str
    body: str

@router.post("/email-to-lead")
async def email_to_lead_webhook(
    payload: InboundEmailPayload,
    user_id: uuid.UUID = Depends(get_current_user_id) # Optional: Can be secured by API Key instead
):
    """
    Webhook to parse forwarded emails and create leads.
    """
    # 1. Archive the inbound email
    inbound = CRMInboundEmail(
        from_email=payload.from_email,
        subject=payload.subject,
        body=payload.body
    )
    await inbound.insert()

    # 2. Find or create contact
    contact = await Contact.find_one(Contact.email == payload.from_email)
    if not contact:
        contact = Contact(
            email=payload.from_email,
            first_name="New",
            last_name="Lead"
        )
        await contact.insert()

    # 3. Find or create lead
    lead = await Lead.find_one(Lead.contact_id == contact.id)
    if not lead:
        lead = Lead(
            contact_id=contact.id,
            company_name=payload.subject or "Email Inquiry",
            source="Inbound Email",
            stage=CRMLeadStage.LEAD,
            assigned_to_id=user_id # Default to whoever set up the webhook or first admin
        )
        await lead.insert()
        inbound.lead_id = lead.id
        await inbound.save()

    # 4. Log activity
    activity = CRMActivity(
        lead_id=lead.id,
        type=ActivityType.SYSTEM,
        content=f"Inbound Email Received: {payload.subject}",
        metadata={"body_preview": payload.body[:200]}
    )
    await activity.insert()

    return {"status": "success", "lead_id": str(lead.id)}
