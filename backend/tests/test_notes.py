import asyncio
import uuid
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.config import settings
from backend.models import User, UserNote, Base, LeadStatusEnum

async def verify_notes():
    engine = create_async_engine(settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Setup a test user
        user_id = uuid.uuid4()
        test_user = User(
            id=user_id,
            email=f"tester_{user_id.hex[:6]}@example.com",
            hashed_password="test_hashed_password",
            first_name="Test",
            last_name="User",
            lead_status="new"
        )
        db.add(test_user)
        
        # 2. Setup an author
        author_id = uuid.uuid4()
        author = User(
            id=author_id,
            email=f"author_{user_id.hex[:6]}@example.com",
            hashed_password="test_hashed_password",
            first_name="Author",
            last_name="User",
            lead_status="new"
        )
        db.add(author)
        await db.commit()
        
        print(f"Created test user {user_id} and author {author_id}")
        
        # 3. Test Note Creation (Service logic)
        from backend.services.users import UserService
        service = UserService(db)
        
        note = await service.create_note(
            user_id=user_id,
            content="First collaborative note!",
            created_by_id=author_id
        )
        print(f"Created note: {note.id} by {note.created_by_id}")
        
        assert note.content == "First collaborative note!"
        assert note.created_by_id == author_id
        
        # 4. Test Fetching
        notes = await service.get_user_notes(user_id)
        print(f"Fetched {len(notes)} notes for user")
        assert len(notes) == 1
        
        # 5. Test Deletion
        success = await service.delete_note(note.id)
        print(f"Deleted note: {success}")
        assert success is True
        
        notes_after = await service.get_user_notes(user_id)
        assert len(notes_after) == 0
        
        print("ALL TESTS PASSED!")
        
        # Cleanup
        await db.delete(test_user)
        await db.delete(author)
        await db.commit()

if __name__ == "__main__":
    asyncio.run(verify_notes())
