import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config import settings

async def migrate():
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    
    async with engine.begin() as conn:
        print("Checking if 'metadata' column exists in 'email_sends' table...")
        result = await conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'email_sends' AND column_name = 'metadata'"
        ))
        row = result.fetchone()
        
        if not row:
            print("Adding 'metadata' column to 'email_sends' table...")
            await conn.execute(sa.text(
                "ALTER TABLE email_sends ADD COLUMN metadata JSONB"
            ))
            print("Successfully added 'metadata' column.")
        else:
            print("'metadata' column already exists.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
