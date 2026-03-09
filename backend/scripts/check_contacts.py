#!/usr/bin/env python
"""Check campaign contacts."""
import asyncio
import uuid
import sys
import os

# Add the project root to sys.path to allow importing the 'backend' package
sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.models import Campaign, Contact

async def check():
    await init_db()
    try:
        # Note: Using a hardcoded ID from the original script for compatibility
        cid = uuid.UUID('27a2ee62-ccbf-42e3-8a92-e1fe58b393da')
        campaign = await Campaign.find_one(Campaign.id == cid)
        
        if not campaign:
            # Fallback to first campaign if hardcoded ID fails
            campaign = await Campaign.find_one()
            
        if campaign:
            print(f'Campaign: {campaign.name}')
            print(f'Contact list ID: {campaign.contact_list_id}')
            
            if campaign.contact_list_id:
                contacts = await Contact.find(Contact.contact_list_id == campaign.contact_list_id).to_list()
                print(f'Contacts: {len(contacts)}')
                for contact in contacts[:5]:
                    print(f'  - {contact.email}')
            else:
                print('No contact list assigned!')
        else:
            print('No campaigns found!')
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(check())
