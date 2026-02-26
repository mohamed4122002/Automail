import asyncio
from backend.db import AsyncSessionLocal
from backend.models import User
from sqlalchemy import select

async def check_users():
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(User).limit(1))
        u = q.scalar_one_or_none()
        if u:
            print(f"USER_ID: {u.id}")
        else:
            print("No users found.")

if __name__ == "__main__":
    asyncio.run(check_users())
