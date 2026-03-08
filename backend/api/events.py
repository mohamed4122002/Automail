from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from ..models import Event

router = APIRouter(
    prefix="/api/events",
    tags=["events"]
)


class EventOut(BaseModel):
    id: str
    type: str
    user_id: str | None = None
    campaign_id: str | None = None
    workflow_id: str | None = None
    workflow_step_id: str | None = None
    email_send_id: str | None = None
    metadata: dict | None = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[EventOut])
async def list_events(limit: int = 100):
    events = await Event.find_all().sort("-created_at").limit(min(limit, 500)).to_list()
    # Convert object id to str manually if needed, but Pydantic should handle if set up correctly
    return [EventOut(
        id=str(e.id),
        type=e.type,
        user_id=str(e.user_id) if e.user_id else None,
        campaign_id=str(e.campaign_id) if e.campaign_id else None,
        workflow_id=str(e.workflow_id) if e.workflow_id else None,
        workflow_step_id=str(e.workflow_step_id) if e.workflow_step_id else None,
        email_send_id=str(e.email_send_id) if e.email_send_id else None,
        metadata=e.metadata
    ) for e in events]
