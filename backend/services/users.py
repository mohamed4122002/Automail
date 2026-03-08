from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from ..models import User, UserNote, EmailSend, Event
from ..schemas.users import UserDetailResponse, UserProfile, UserNote as UserNoteSchema, UserTimelineEvent
from ..schemas.utils import orm_to_pydantic, orm_list_to_pydantic

class UserService:
    def __init__(self):
        pass

    async def get_users(self) -> list[User]:
        return await User.find_all().sort("-created_at").to_list()

    async def get_user_detail(self, user_id: UUID) -> Optional[UserDetailResponse]:
        user = await User.find_one(User.id == user_id)
        
        if not user:
            return None
            
        notes = await UserNote.find(UserNote.user_id == user_id).sort("-created_at").to_list()
        
        # Real Timeline from EmailSend and Event tables
        emails = await EmailSend.find(EmailSend.user_id == user_id).sort("-created_at").limit(50).to_list()
        events = await Event.find(Event.user_id == user_id).sort("-created_at").limit(50).to_list()
        
        timeline_events = []
        for e in emails:
            desc = getattr(e, 'subject', getattr(e, 'template_id', 'Email Sent'))
            timeline_events.append(UserTimelineEvent(
                id=str(e.id),
                type="email_sent",
                content=str(desc),
                date=e.created_at.isoformat()
            ))
            
        for ev in events:
            timeline_events.append(UserTimelineEvent(
                id=str(ev.id),
                type=ev.type,
                content=ev.type,
                date=ev.created_at.isoformat()
            ))
            
        timeline_events.sort(key=lambda x: x.date, reverse=True)
        timeline_events = timeline_events[:50]

        return UserDetailResponse(
            user=orm_to_pydantic(user, UserProfile),
            timeline=timeline_events,
            notes=orm_list_to_pydantic(notes, UserNoteSchema)
        )

    async def claim_lead(self, user_id: UUID, claimer_id: UUID) -> User:
        user = await User.find_one(User.id == user_id)
        
        if not user:
            raise ValueError("Lead not found")
        
        claimed_by_id = getattr(user, 'claimed_by_id', None)
        if claimed_by_id:
            raise ValueError(f"Lead already claimed by {claimed_by_id}")
            
        user.claimed_by_id = claimer_id # Dynamic field on Beanie document
        user.claimed_at = datetime.utcnow()
        
        await user.save()
        return user

    async def create_note(self, user_id: UUID, content: str, created_by_id: Optional[UUID] = None) -> UserNote:
        note = UserNote(
            user_id=user_id, 
            content=content, 
            created_by_id=created_by_id
        )
        await note.insert()
        
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
            print(f"Failed to broadcast note event: {e}")
            
        return note

    async def delete_note(self, note_id: UUID) -> bool:
        note = await UserNote.find_one(UserNote.id == note_id)
        
        if not note:
            return False
            
        user_id = note.user_id
        await note.delete()
        
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
        return await UserNote.find(UserNote.user_id == user_id).sort("-created_at").to_list()
