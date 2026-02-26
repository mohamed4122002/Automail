import asyncio
import uuid
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from backend.models import User
from backend.config import settings

async def verify_lead_claim():
    # Force asyncpg for the test
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Get a random user who is not claimed
        result = await db.execute(select(User).where(User.claimed_by_id == None).limit(1))
        lead = result.scalar_one_or_none()
        
        if not lead:
            print("No unclaimed leads found for testing.")
            return

        print(f"Testing claim for lead: {lead.email} ({lead.id})")
        
        # 2. Get another user to be the claimer
        result = await db.execute(select(User).where(User.id != lead.id).limit(1))
        claimer = result.scalar_one_or_none()
        
        if not claimer:
            print("No potential claimers found.")
            return

        print(f"Claimer: {claimer.email} ({claimer.id})")

        # 3. Simulate claim
        from backend.services.users import UserService
        service = UserService(db)
        
        try:
            print("Attempting to claim...")
            updated_lead = await service.claim_lead(lead.id, claimer.id)
            print(f"SUCCESS: Lead claimed by {updated_lead.claimed_by_id} at {updated_lead.claimed_at}")
            
            # 4. Attempt to claim again (should fail)
            print("Attempting to claim again (expecting failure)...")
            try:
                await service.claim_lead(lead.id, claimer.id)
                print("FAILURE: Lead was claimed twice!")
            except ValueError as e:
                print(f"CORRECTLY FAILED: {str(e)}")
                
        except Exception as e:
            print(f"ERROR: {str(e)}")
        finally:
            # We don't rollback because we want to see the change in DB if we check manually, 
            # but for a test script we usually should. Here we'll just print success.
            pass

if __name__ == "__main__":
    asyncio.run(verify_lead_claim())
