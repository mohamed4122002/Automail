from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from ..db import get_db
from ..services.users import UserService
from ..schemas.users import UserDetailResponse, UserNoteCreate, UserNote, UserProfile
from ..schemas.utils import orm_to_pydantic
from .deps import get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=list[UserDetailResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    users = await service.get_users()
    return [
        UserDetailResponse(
            user=orm_to_pydantic(u, UserProfile),
            timeline=[],
            notes=[]
        ) for u in users
    ]

@router.get("/{id}", response_model=UserDetailResponse)
async def get_user_detail(id: UUID, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.get_user_detail(id)

@router.get("/{id}/notes", response_model=list[UserNote])
async def get_notes_for_user(id: UUID, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.get_user_notes(id)

@router.post("/{id}/notes", response_model=UserNote)
async def create_user_note(
    id: UUID, 
    note: UserNoteCreate, 
    db: AsyncSession = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    service = UserService(db)
    return await service.create_note(user_id=id, content=note.content, created_by_id=current_user_id)

@router.post("/{id}/claim")
async def claim_lead(
    id: UUID, 
    db: AsyncSession = Depends(get_db), 
    current_user_id: UUID = Depends(get_current_user_id)
):
    service = UserService(db)
    try:
        user = await service.claim_lead(user_id=id, claimer_id=current_user_id)
        return {"status": "success", "claimed_by": user.claimed_by_id, "claimed_at": user.claimed_at}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
