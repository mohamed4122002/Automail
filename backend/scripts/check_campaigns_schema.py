import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config import settings

async def check_schema():
    # Use the async URL from config (which might need adaptation)
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    
    async with engine.connect() as conn:
        print(f"Checking columns for table 'campaigns'...")
        # Query information_schema
        result = await conn.execute(sa.text(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'campaigns'"
        ))
        columns = result.fetchall()
        
        if not columns:
            print("Table 'campaigns' not found!")
        else:
            print("Found columns:")
            column_names = []
            for col in columns:
                print(f" - {col[0]} ({col[1]})")
                column_names.append(col[0])
            
            if "contact_list_id" in column_names:
                print("\nSUCCESS: 'contact_list_id' EXISTS.")
            else:
                print("\nFAILURE: 'contact_list_id' IS MISSING.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_schema())
