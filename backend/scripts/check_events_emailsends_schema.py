import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config import settings

async def check_schema():
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    
    async with engine.connect() as conn:
        for table in ['events', 'email_sends']:
            print(f"\nChecking columns for table '{table}'...")
            result = await conn.execute(sa.text(
                f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'"
            ))
            columns = result.fetchall()
            
            if not columns:
                print(f"Table '{table}' not found!")
            else:
                for col in columns:
                    print(f" - {col[0]} ({col[1]})")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_schema())
