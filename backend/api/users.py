from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from ..services.users import UserService
from ..schemas.users import UserDetailResponse, UserNoteCreate, UserNote, UserProfile
from ..schemas.utils import orm_to_pydantic
from .deps import get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=list[UserDetailResponse])
async def list_users():
    service = UserService()
    users = await service.get_users()
    return [
        UserDetailResponse(
            user=orm_to_pydantic(u, UserProfile),
            timeline=[],
            notes=[]
        ) for u in users
    ]

@router.get("/{id}", response_model=UserDetailResponse)
async def get_user_detail(id: UUID):
    service = UserService()
    detail = await service.get_user_detail(id)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")
    return detail

@router.get("/{id}/notes", response_model=list[UserNote])
async def get_notes_for_user(id: UUID):
    service = UserService()
    return await service.get_user_notes(id)

@router.post("/{id}/notes", response_model=UserNote)
async def create_user_note(
    id: UUID, 
    note: UserNoteCreate, 
    current_user_id: UUID = Depends(get_current_user_id)
):
    service = UserService()
    return await service.create_note(user_id=id, content=note.content, created_by_id=current_user_id)

@router.post("/{id}/claim")
async def claim_lead(
    id: UUID, 
    current_user_id: UUID = Depends(get_current_user_id)
):
    service = UserService()
    try:
        user = await service.claim_lead(user_id=id, claimer_id=current_user_id)
        # Using getattr to safely handle the dynamic attribute used in claim_lead originally
        claimed_by_id = getattr(user, 'claimed_by_id', None)
        claimed_at = getattr(user, 'claimed_at', None)
        return {"status": "success", "claimed_by": claimed_by_id, "claimed_at": claimed_at}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
