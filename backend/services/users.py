import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID
from ..models import User, UserNote
from ..schemas.users import UserDetailResponse, UserProfile, UserNote as UserNoteSchema, UserTimelineEvent
from ..schemas.utils import orm_to_pydantic, orm_list_to_pydantic

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_users(self) -> list[User]:
        query = sa.select(User).order_by(User.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_detail(self, user_id: UUID) -> UserDetailResponse:
        query = sa.select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return None # Handle 404 in API layer
            
        # Notes
        notes_query = sa.select(UserNote).where(UserNote.user_id == user_id).order_by(UserNote.created_at.desc())
        notes_res = await self.db.execute(notes_query)
        notes = notes_res.scalars().all()
        
        # Real Timeline from EmailSend and Event tables
        from ..models import EmailSend, Event
        
        # Get email sends
        email_timeline_query = sa.select(
            EmailSend.id.label('id'),
            EmailSend.created_at.label('timestamp'),
            EmailSend.subject.label('description')
        ).where(EmailSend.user_id == user_id)
        
        # Get events
        event_timeline_query = sa.select(
            Event.id.label('id'),
            Event.created_at.label('timestamp'),
            Event.type.label('description')
        ).where(Event.user_id == user_id)
        
        # Combine and order
        timeline_result = await self.db.execute(
            sa.union_all(email_timeline_query, event_timeline_query)
            .order_by(sa.text('timestamp desc'))
            .limit(50)
        )
        
        timeline_events = [
            UserTimelineEvent(
                id=str(row.id),
                type="email_sent" if hasattr(row, 'subject') else str(row.description),
                content=str(row.description),
                date=row.timestamp.isoformat()
            )
            for row in timeline_result.all()
        ]

        return UserDetailResponse(
            user=orm_to_pydantic(user, UserProfile),
            timeline=timeline_events,
            notes=orm_list_to_pydantic(notes, UserNoteSchema)
        )

    async def claim_lead(self, user_id: UUID, claimer_id: UUID) -> User:
        query = sa.select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Lead not found")
        
        if user.claimed_by_id:
            raise ValueError(f"Lead already claimed by {user.claimed_by_id}")
            
        from datetime import datetime
        user.claimed_by_id = claimer_id
        user.claimed_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def create_note(self, user_id: UUID, content: str, created_by_id: Optional[UUID] = None) -> UserNote:
        note = UserNote(
            user_id=user_id, 
            content=content, 
            created_by_id=created_by_id
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        
        # Real-time notification
        try:
            from ..api.realtime import broadcast_event
            await broadcast_event({
                "type": "new_note",
                "user_id": str(user_id),
                "author_id": str(created_by_id) if created_by_id else None,
                "content_preview": content[:50] + "..." if len(content) > 50 else content
            })
        except Exception as e:
            # Don't fail the whole request if broadcast fails
            print(f"Failed to broadcast note event: {e}")
            
        return note

    async def delete_note(self, note_id: UUID) -> bool:
        query = sa.select(UserNote).where(UserNote.id == note_id)
        result = await self.db.execute(query)
        note = result.scalar_one_or_none()
        
        if not note:
            return False
            
        user_id = note.user_id
        await self.db.delete(note)
        await self.db.commit()
        
        # Optional: Notifying deletion
        try:
            from ..api.realtime import broadcast_event
            await broadcast_event({
                "type": "delete_note",
                "user_id": str(user_id),
                "note_id": str(note_id)
            })
        except:
            pass
            
        return True

    async def get_user_notes(self, user_id: UUID) -> list[UserNote]:
        query = sa.select(UserNote).where(UserNote.user_id == user_id).order_by(UserNote.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()
