from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import List
from ..services.notifications import NotificationService
from ..models import CRMNotification
from .deps import get_current_user_id

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("", response_model=List[CRMNotification])
async def get_notifications(
    limit: int = 20,
    current_user_id: UUID = Depends(get_current_user_id)
):
    return await NotificationService.get_user_notifications(current_user_id, limit)

@router.post("/{id}/read")
async def mark_read(
    id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    await NotificationService.mark_as_read(id)
    return {"status": "success"}

@router.post("/mark-all-read")
@router.post("/read-all")
async def mark_all_read(
    current_user_id: UUID = Depends(get_current_user_id)
):
    await NotificationService.mark_all_as_read(current_user_id)
    return {"status": "success"}
