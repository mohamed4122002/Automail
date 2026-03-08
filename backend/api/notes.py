from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from ..services.users import UserService
from .deps import get_current_user_id

router = APIRouter(prefix="/notes", tags=["notes"])

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    service = UserService()
    success = await service.delete_note(id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return None
