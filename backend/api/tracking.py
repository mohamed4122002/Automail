from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import sqlalchemy as sa

from ..db import get_db
from ..models import Event, EmailSend, EventTypeEnum
from ..tasks import _broadcast_event_to_websocket

router = APIRouter(prefix="/track", tags=["tracking"])

@router.get("/click/{email_send_id}")
async def track_click(
    email_send_id: UUID,
    url: str = Query(..., description="Target URL to redirect to"),
    db: AsyncSession = Depends(get_db)
):
    """
    Track a link click from an email.
    
    Actions:
    1. Find EmailSend record
    2. Log CLICKED event
    3. Broadcast 'hot_lead' via WebSocket
    4. Redirect to target URL
    """
    
    # 1. Find EmailSend
    res = await db.execute(
        sa.select(EmailSend)
        .options(sa.orm.selectinload(EmailSend.campaign))
        .where(EmailSend.id == email_send_id)
    )
    email_send = res.scalar_one_or_none()
    
    if not email_send:
        # Still redirect if email_send not found (don't break user experience)
        return RedirectResponse(url=url)
    
    # 2. Record Event
    event = Event(
        type=EventTypeEnum.CLICKED,
        user_id=email_send.user_id,
        campaign_id=email_send.campaign_id,
        workflow_id=email_send.workflow_id,
        workflow_step_id=email_send.workflow_step_id,
        email_send_id=email_send.id,
        data={
            "target_url": url,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    db.add(event)
    
    # Flush to ensure event is in DB if needed by broadcast or other logic
    await db.flush()
    
    # 3. Broadcast Hot Lead
    # Note: _broadcast_event_to_websocket is async-safe but usually called in asyncio.run
    # Here we are already in an async context.
    await _broadcast_event_to_websocket(
        event_type="clicked",
        user_id=str(email_send.user_id),
        user_email=email_send.to_email,
        campaign_id=str(email_send.campaign_id) if email_send.campaign_id else None,
        campaign_name=email_send.campaign.name if email_send.campaign else None
    )
    
    await db.commit()
    
    # 4. Redirect
    return RedirectResponse(url=url)


@router.get("/open/{email_send_id}")
async def track_open(
    email_send_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Track an email open via a tracking pixel.
    
    Actions:
    1. Find EmailSend record
    2. Log OPENED event
    3. Broadcast 'opened' via WebSocket
    4. Return transparent pixel
    """
    from fastapi.responses import Response
    
    # 1. Find EmailSend
    res = await db.execute(
        sa.select(EmailSend)
        .options(sa.orm.selectinload(EmailSend.campaign))
        .where(EmailSend.id == email_send_id)
    )
    email_send = res.scalar_one_or_none()
    
    if email_send:
        # 2. Record Event
        event = Event(
            type=EventTypeEnum.OPENED,
            user_id=email_send.user_id,
            campaign_id=email_send.campaign_id,
            workflow_id=email_send.workflow_id,
            workflow_step_id=email_send.workflow_step_id,
            email_send_id=email_send.id,
            data={
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        db.add(event)
        
        # 3. Broadcast
        await _broadcast_event_to_websocket(
            event_type="opened",
            user_id=str(email_send.user_id),
            user_email=email_send.to_email,
            campaign_id=str(email_send.campaign_id) if email_send.campaign_id else None,
            campaign_name=email_send.campaign.name if email_send.campaign else None
        )
        
        await db.commit()
    
    # 4. Return 1x1 transparent GIF pixel
    pixel_data = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    return Response(content=pixel_data, media_type="image/gif")
