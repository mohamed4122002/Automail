import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.config import settings
from backend.services.campaign_analytics import CampaignAnalyticsService
from backend.models import Campaign, User

async def verify_analytics():
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        service = CampaignAnalyticsService(db)
        
        # We need a valid campaign_id. Let's try to get one from the DB or use a dummy one.
        # If the campaign doesn't exist, we'll get an error, but that's okay, we're testing the TypeError.
        # The TypeError happens inside _get_top_links which is called by get_analytics.
        
        try:
            # Try to find a real campaign first
            result = await db.execute(sa.text("SELECT id FROM campaigns LIMIT 1"))
            row = result.fetchone()
            if row:
                campaign_id = row[0]
                print(f"Testing with real campaign_id: {campaign_id}")
            else:
                campaign_id = uuid.uuid4()
                print(f"No campaigns found. Testing with dummy campaign_id: {campaign_id}")
            
            # This should NOT raise TypeError: 'MetaData' object is not subscriptable
            await service.get_analytics(campaign_id)
            print("SUCCESS: get_analytics called without TypeError.")
            
        except Exception as e:
            if "MetaData' object is not subscriptable" in str(e):
                print(f"FAILURE: TypeError still persists: {e}")
            elif "not found" in str(e).lower() or "Campaign" in str(e):
                # This is expected if campaign doesn't exist, but it means we got past the TypeError
                print(f"SUCCESS: Got past TypeError (Expected error: {e})")
            else:
                print(f"Caught other error (but not the target TypeError): {e}")

    await engine.dispose()

if __name__ == "__main__":
    import sqlalchemy as sa
    asyncio.run(verify_analytics())
