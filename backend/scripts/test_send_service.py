import asyncio
import uuid
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.config import settings
from backend.services.campaign_analytics import CampaignAnalyticsService

async def test_send():
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        service = CampaignAnalyticsService(db)
        
        # We need a campaign_id and an email
        # Let's try to find one
        import sqlalchemy as sa
        result = await db.execute(sa.text("SELECT id FROM campaigns LIMIT 1"))
        row = result.fetchone()
        if not row:
            print("No campaigns found")
            return
            
        campaign_id = row[0]
        test_email = "mohmedessam166202@gmail.com"
        
        print(f"Testing send_test_email for campaign {campaign_id} to {test_email}...")
        
        try:
            # Use a timeout because the user said "nothing happen"
            result = await asyncio.wait_for(
                service.send_test_email(
                    campaign_id=campaign_id,
                    recipient_emails=[test_email],
                    use_campaign_workflow=True
                ),
                timeout=15.0
            )
            print(f"RESULT: {result}")
        except asyncio.TimeoutError:
            print("TIMEOUT: send_test_email hung!")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_send())
