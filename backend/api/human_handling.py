from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, exists
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
import io
import csv

from ..db import get_db
from ..models import User, Event, EventTypeEnum
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/human-handling-list")
async def get_human_handling_list(
    days: int = Query(30, description="Look back period in days"),
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(get_current_user_id)
):
    """
    Get list of users who opened emails but didn't click links.
    These users need human follow-up (Path 2 from vision).
    
    Filters:
    - Has at least one OPENED event
    - Has NO CLICKED events
    - Within specified time period
    """
    
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    
    # Subquery: Users who have opened emails
    opened_subquery = select(Event.user_id).where(
        and_(
            Event.type == EventTypeEnum.OPENED,
            Event.created_at >= since
        )
    ).distinct()
    
    # Subquery: Users who have clicked
    clicked_subquery = select(Event.user_id).where(
        and_(
            Event.type == EventTypeEnum.CLICKED,
            Event.created_at >= since
        )
    ).distinct()
    
    # Main query: Users who opened but didn't click
    query = select(User).where(
        and_(
            User.id.in_(opened_subquery),
            ~User.id.in_(clicked_subquery)
        )
    )
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get additional data for each user
    user_list = []
    for user in users:
        # Get last opened event
        last_open_query = select(Event).where(
            and_(
                Event.user_id == user.id,
                Event.type == EventTypeEnum.OPENED,
                Event.created_at >= since
            )
        ).order_by(Event.created_at.desc()).limit(1)
        
        last_open_result = await db.execute(last_open_query)
        last_open = last_open_result.scalar_one_or_none()
        
        if last_open:
            days_since_open = (datetime.utcnow() - last_open.created_at).days
            
            user_list.append({
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "last_email_opened": last_open.created_at.isoformat(),
                "days_since_open": days_since_open,
                "lead_status": user.lead_status,
                "contacted": user.lead_status == "contacted"
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
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(get_current_user_id)
):
    """
    Export human handling list to CSV for sales team.
    """
    
    # Get the data using the same logic
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    
    opened_subquery = select(Event.user_id).where(
        and_(
            Event.type == EventTypeEnum.OPENED,
            Event.created_at >= since
        )
    ).distinct()
    
    clicked_subquery = select(Event.user_id).where(
        and_(
            Event.type == EventTypeEnum.CLICKED,
            Event.created_at >= since
        )
    ).distinct()
    
    query = select(User).where(
        and_(
            User.id.in_(opened_subquery),
            ~User.id.in_(clicked_subquery)
        )
    )
    
    result = await db.execute(query)
    users = result.scalars().all()
    
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
        last_open_query = select(Event).where(
            and_(
                Event.user_id == user.id,
                Event.type == EventTypeEnum.OPENED,
                Event.created_at >= since
            )
        ).order_by(Event.created_at.desc()).limit(1)
        
        last_open_result = await db.execute(last_open_query)
        last_open = last_open_result.scalar_one_or_none()
        
        if last_open:
            days_since_open = (datetime.utcnow() - last_open.created_at).days
            
            writer.writerow([
                user.email,
                user.first_name or '',
                user.last_name or '',
                last_open.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                days_since_open,
                user.lead_status or 'unknown'
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
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(get_current_user_id)
):
    """
    Mark a user as contacted by sales team.
    Updates lead_status to 'contacted'.
    """
    
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    
    user.lead_status = "contacted"
    await db.commit()
    
    return {
        "message": "User marked as contacted",
        "user_id": str(user_id),
        "lead_status": "contacted"
    }
