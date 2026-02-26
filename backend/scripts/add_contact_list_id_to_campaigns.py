import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config import settings

async def apply_migration():
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    
    async with engine.begin() as conn:
        print("Adding 'contact_list_id' column to 'campaigns' table...")
        # Add column
        await conn.execute(sa.text(
            "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS contact_list_id UUID;"
        ))
        
        # Add foreign key constraint
        print("Adding foreign key constraint...")
        await conn.execute(sa.text(
            "ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS fk_campaigns_contact_list_id_contact_lists;"
        ))
        await conn.execute(sa.text(
            "ALTER TABLE campaigns ADD CONSTRAINT fk_campaigns_contact_list_id_contact_lists "
            "FOREIGN KEY (contact_list_id) REFERENCES contact_lists(id) ON DELETE SET NULL;"
        ))
        
        print("Migration applied successfully.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(apply_migration())
