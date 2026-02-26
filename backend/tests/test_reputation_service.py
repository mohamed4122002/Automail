import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.services.analytics import AnalyticsService
from backend.config import settings
from uuid import UUID
import json

async def test_reputation():
    # Force asyncpg for the test
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        service = AnalyticsService(db)
        
        # We need a user_id. Let's find one from the DB
        from sqlalchemy import text
        result = await db.execute(text("SELECT id FROM users LIMIT 1"))
        user_id = result.scalar()
        
        if not user_id:
            print("No users found in database.")
            return

        print(f"Testing reputation for user: {user_id}")
        reputation = await service.get_sender_reputation(owner_id=user_id)
        
        print("\n--- Reputation Score ---")
        print(json.dumps(reputation, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(test_reputation())
