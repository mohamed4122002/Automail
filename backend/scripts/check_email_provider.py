import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config import settings

async def check_provider():
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    
    async with engine.connect() as conn:
        print("Checking 'email_provider' setting...")
        result = await conn.execute(sa.text(
            "SELECT value FROM settings WHERE key = 'email_provider'"
        ))
        row = result.fetchone()
        
        if row:
            print(f"Current email provider config: {row[0]}")
        else:
            print("No 'email_provider' setting found (will fallback to ConsoleProvider).")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_provider())
