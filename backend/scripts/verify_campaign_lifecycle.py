import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from backend.models import Campaign, ContactList, Workflow, WorkflowInstance, Contact, Lead
from backend.services.campaign_manager import CampaignManagerService
from backend.db import Base

# Setup local test DB connection (adjust if needed)
DATABASE_URL = "postgresql+asyncpg://automation_user:Mm01151800275@localhost:5432/marketing_automation"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def verify_lifecycle():
    async with AsyncSessionLocal() as db:
        print("--- Starting Verification ---")
        
        # 1. Use a real user ID found in the database
        OWNER_ID = uuid.UUID("40058144-5e61-4a9c-91b1-4f61563a6ae5")
        
        # 2. Create a test list
        test_list = ContactList(name="Verification List", owner_id=OWNER_ID)
        db.add(test_list)
        await db.flush()
        
        # 3. Add test contacts
        c1 = Contact(contact_list_id=test_list.id, email="test1@example.com", first_name="Test", last_name="One")
        db.add(c1)
        await db.flush()
        
        # 4. Create a test campaign
        campaign = Campaign(name="Verification Campaign", owner_id=OWNER_ID, contact_list_id=test_list.id)
        db.add(campaign)
        await db.flush()
        
        # 5. Create a test workflow linked to campaign
        workflow = Workflow(name="Verification Workflow", campaign_id=campaign.id)
        db.add(workflow)
        await db.commit()
        
        print(f"Entities created: List({test_list.id}), Campaign({campaign.id}), Workflow({workflow.id})")
        
        # 6. Activate Campaign via Manager
        manager = CampaignManagerService(db)
        print("Activating campaign...")
        result = await manager.activate_campaign(campaign.id, campaign.owner_id)
        print(f"Activation Result: {result}")
        
        # 7. Verify Instances
        q = await db.execute(select(WorkflowInstance).where(WorkflowInstance.workflow_id == workflow.id))
        instances = q.scalars().all()
        print(f"Workflow Instances created: {len(instances)}")
        
        if len(instances) > 0:
            print("SUCCESS: Campaign lifecycle verified.")
        else:
            print("FAILURE: No instances created.")
            
        # Cleanup (Optional)
        # await db.delete(workflow)
        # await db.delete(campaign)
        # ...

if __name__ == "__main__":
    asyncio.run(verify_lifecycle())
