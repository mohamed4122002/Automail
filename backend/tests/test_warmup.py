import asyncio
import uuid
import threading
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.config import settings
from backend.models import Campaign, EmailSend, User, WorkflowStep, WorkflowNode
from backend.tasks import send_email_task
from backend.services.reputation import ReputationWarmupService
from redis import Redis

async def verify_warmup():
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    async with async_session() as db:
        # 1. Setup Data
        # Ensure we have a user
        from sqlalchemy import text
        res_user = await db.execute(text("SELECT id FROM users LIMIT 1"))
        user_id = res_user.scalar()
        if not user_id:
            user = User(email=f"test_{uuid.uuid4().hex[:6]}@example.com")
            db.add(user)
            await db.commit()
            user_id = user.id

        # Create Campaign with low warmup limit
        campaign = Campaign(
            name=f"Warmup Test {uuid.uuid4().hex[:6]}",
            owner_id=user_id,
            warmup_config={
                "enabled": True,
                "initial_volume": 2,
                "daily_increase_pct": 50.0,
                "max_volume": 100,
                "current_limit": 2
            }
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        
        # Clear Redis counter for this campaign
        service = ReputationWarmupService(db, redis)
        redis.delete(service._get_daily_key(campaign.id))
        
        # Create 3 EmailSend records
        email_sends = []
        for i in range(3):
            es = EmailSend(
                campaign_id=campaign.id,
                user_id=user_id,
                to_email=f"recipient_{i}@example.com",
                status="pending",
                unsubscribe_token=str(uuid.uuid4())
            )
            db.add(es)
            email_sends.append(es)
        await db.commit()
        for es in email_sends: await db.refresh(es)

        print(f"Triggering 3 emails for campaign {campaign.id} with limit 2...")
        
        # Call the task logic directly. We need to handle the session carefully.
        # Since send_email_task uses asyncio.run() internally, we can't call it from here easily 
        # while an event loop is already running. 
        # Let's instead test the ReputationWarmupService directly or use a subprocess.
        
        # Test Check Limit Logic
        print("Testing limit checks...")
        can_send_1 = await service.check_warmup_limit(campaign.id)
        print(f"Can send 1st: {can_send_1}")
        await service.increment_sent_count(campaign.id)
        
        can_send_2 = await service.check_warmup_limit(campaign.id)
        print(f"Can send 2nd: {can_send_2}")
        await service.increment_sent_count(campaign.id)
        
        can_send_3 = await service.check_warmup_limit(campaign.id)
        print(f"Can send 3rd (expect False): {can_send_3}")
        
        sent_today = int(redis.get(service._get_daily_key(campaign.id)) or 0)
        print(f"Emails recorded in Redis: {sent_today}")
        
        if not can_send_3 and sent_today == 2:
            print("SUCCESS: Volume capping logic verified!")
        else:
            print(f"FAILURE: Expected cap at 2, got {sent_today}")

        # 2. Test Daily Increase
        print("\nTesting daily limit increase...")
        # Update last increase to yesterday to allow increase today
        await db.execute(
            sa.update(Campaign)
            .where(Campaign.id == campaign.id)
            .values(warmup_last_limit_increase=datetime.utcnow() - timedelta(days=1))
        )
        await db.commit()
        
        increased = await service.process_daily_increase()
        
        # Refresh campaign from DB
        res = await db.execute(sa.select(Campaign).where(Campaign.id == campaign.id))
        campaign = res.scalar_one()
        
        new_limit = campaign.warmup_config["current_limit"]
        print(f"Increased processed. New limit: {new_limit}")
        
        # 2 + ceil(2 * 0.5) = 2 + 1 = 3
        if new_limit == 3:
            print("SUCCESS: Daily increase worked!")
        else:
            print(f"FAILURE: Expected limit 3, got {new_limit}")

if __name__ == "__main__":
    import sqlalchemy as sa
    asyncio.run(verify_warmup())
