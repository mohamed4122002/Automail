from typing import List

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_active_user
from ..db import get_db
from ..models import Event


router = APIRouter(
    prefix="/api/events",
    tags=["events"],
    dependencies=[Depends(get_current_active_user)],
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
        orm_mode = True


@router.get("/", response_model=List[EventOut])
async def list_events(
    limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Event]:
    result = await db.execute(
        sa.select(Event)
        .order_by(Event.created_at.desc())
        .limit(min(limit, 500))
    )
    return list(result.scalars().all())

