import asyncio
import sys
import os

# Add the project root to sys.path to allow importing the 'backend' package
sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.models import Campaign, Contact, ContactList, WorkflowInstance

async def check_db():
    await init_db()
    try:
        # Check campaigns
        campaign_count = await Campaign.count()
        print(f"Campaigns: {campaign_count}")
        
        # Check contact lists
        list_count = await ContactList.count()
        print(f"Contact Lists: {list_count}")
        
        # Check contacts
        contact_count = await Contact.count()
        print(f"Contacts: {contact_count}")
        
        # Check workflow instances
        wi_count = await WorkflowInstance.count()
        print(f"Workflow Instances: {wi_count}")
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(check_db())
