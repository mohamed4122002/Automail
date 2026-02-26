
import asyncio
import uuid
from backend.db import AsyncSessionLocal
from backend.services.campaign_manager import CampaignManagerService
from backend.models import User

async def force_activate(campaign_id_str):
    campaign_id = uuid.UUID(campaign_id_str)
    async with AsyncSessionLocal() as db:
        # Get an owner ID (any user with campaign access)
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
            print("No user found")
            return
            
        service = CampaignManagerService(db)
        print(f"Force activating campaign {campaign_id_str} with owner {user.id}")
        result = await service.activate_campaign(campaign_id, user.id)
        print(f"Result: {result}")

if __name__ == "__main__":
    from sqlalchemy import select
    cid = "27a2ee62-ccbf-42e3-8a92-e1fe58b393da"
    asyncio.run(force_activate(cid))
