#!/usr/bin/env python
"""Check campaign contacts."""
import asyncio
import uuid
from backend.db import AsyncSessionLocal
from backend.models import Campaign, Contact
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        cid = uuid.UUID('27a2ee62-ccbf-42e3-8a92-e1fe58b393da')
        r = await db.execute(select(Campaign).where(Campaign.id == cid))
        c = r.scalar_one()
        print(f'Contact list ID: {c.contact_list_id}')
        
        if c.contact_list_id:
            r2 = await db.execute(select(Contact).where(Contact.contact_list_id == c.contact_list_id))
            contacts = r2.scalars().all()
            print(f'Contacts: {len(contacts)}')
            for contact in contacts[:5]:
                print(f'  - {contact.email}')
        else:
            print('No contact list assigned!')

if __name__ == "__main__":
    asyncio.run(check())
