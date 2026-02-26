import asyncio
from backend.db import AsyncSessionLocal
from backend.models import Campaign, Contact, ContactList, WorkflowInstance
from sqlalchemy import select, func

async def check_db():
    async with AsyncSessionLocal() as db:
        # Check campaigns
        campaign_count = await db.execute(select(func.count(Campaign.id)))
        print(f"Campaigns: {campaign_count.scalar_one()}")
        
        # Check contact lists
        list_count = await db.execute(select(func.count(ContactList.id)))
        print(f"Contact Lists: {list_count.scalar_one()}")
        
        # Check contacts
        contact_count = await db.execute(select(func.count(Contact.id)))
        print(f"Contacts: {contact_count.scalar_one()}")
        
        # Check workflow instances
        wi_count = await db.execute(select(func.count(WorkflowInstance.id)))
        print(f"Workflow Instances: {wi_count.scalar_one()}")

if __name__ == "__main__":
    asyncio.run(check_db())
