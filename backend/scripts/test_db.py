import asyncio
import uuid
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base
from backend.models import Campaign, User

DATABASE_URL = "postgresql+asyncpg://automation_user:Mm01151800275@localhost:5432/marketing_automation"

async def test():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        uid = uuid.uuid4()
        user = User(
            id=uid,
            email=f"test_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="...",
            first_name="T",
            last_name="T"
        )
        db.add(user)
        # We MUST commit or flush for foreign key to see it if it's checked immediately
        await db.flush()
        
        cid = uuid.uuid4()
        camp = Campaign(
            id=cid,
            name="Test Camp",
            owner_id=uid
        )
        db.add(camp)
        try:
            await db.commit()
            print("SUCCESS: User and Campaign created.")
        except Exception as e:
            print(f"FAILED: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(test())
