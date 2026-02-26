import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config import settings

async def reset():
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    
    async with engine.connect() as conn:
        print("Deleting existing email_provider setting...")
        await conn.execute(sa.text(
            "DELETE FROM settings WHERE key = 'email_provider'"
        ))
        await conn.commit()
        print("Reset successful.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset())
