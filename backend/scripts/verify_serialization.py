import asyncio
import sqlalchemy as sa
from sqlalchemy.orm import selectinload
from backend.db import AsyncSessionLocal
from backend.models import Campaign
from backend.schemas.campaigns import CampaignOut
import json

async def verify_serialization():
    async with AsyncSessionLocal() as db:
        print("--- Verifying Campaign Serialization ---")
        
        # 1. Fetch a campaign with eager loading
        result = await db.execute(
            sa.select(Campaign).options(selectinload(Campaign.workflow)).limit(1)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            print("No campaign found to test. Creating a dummy one...")
            # Use a real user ID from your DB if possible, or omit owner check if testing just serialization
            from uuid import uuid4
            campaign = Campaign(
                id=uuid4(),
                name="Test Serial",
                owner_id=uuid4() # Mock ID
            )
            db.add(campaign)
            await db.flush()
        
        print(f"Testing serialization for Campaign: {campaign.name} ({campaign.id})")
        
        try:
            # Simulate FastAPI serialization
            pydantic_obj = CampaignOut.model_validate(campaign)
            json_data = pydantic_obj.model_dump_json()
            print("SUCCESS: Serialization completed without MissingGreenlet error.")
            # print(f"Output: {json_data[:100]}...")
        except Exception as e:
            print(f"FAILURE: Serialization failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_serialization())
