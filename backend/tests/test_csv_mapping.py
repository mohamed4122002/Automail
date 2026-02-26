import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models import Contact, ContactList, User
from backend.config import settings
from backend.api.contacts import validate_email_format
from backend.db import AsyncSessionLocal
from redis import Redis

import asyncio
import uuid
import csv
import io
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.db import engine, AsyncSessionLocal

async def test_csv_mapping():
    print("Testing CSV Mapping Logic...")
    
    # 1. Setup mock data
    csv_content = "Customer Email,Given Name,Family Name,Phone\ntest1@example.com,John,Doe,123456\ntest2@example.com,Jane,Smith,789012"
    mapping = {
        "Email": "Customer Email",
        "First Name": "Given Name",
        "Last Name": "Family Name"
    }
    
    # 2. Extract and Validate
    csv_data = io.StringIO(csv_content)
    reader = csv.DictReader(csv_data)
    rows = list(reader)
    
    print(f"Read {len(rows)} rows from mock CSV")
    
    async with AsyncSessionLocal() as db:
        # 1. Create a test user for ownership
        user_id = uuid.uuid4()
        test_user = User(
            id=user_id,
            email=f"tester_{user_id.hex[:6]}@example.com",
            hashed_password="test_hashed_password",
            first_name="Test",
            last_name="User"
        )
        db.add(test_user)
        await db.commit()
        
        # 2. Create a test list
        list_id = uuid.uuid4()
        test_list = ContactList(id=list_id, name="Test Mapping List", owner_id=user_id)
        db.add(test_list)
        await db.commit()
        
        imported = 0
        for row in rows:
            email_col = mapping.get("Email")
            first_name_col = mapping.get("First Name")
            last_name_col = mapping.get("Last Name")
            
            email = row.get(email_col, "").strip().lower()
            is_valid, _ = validate_email_format(email)
            
            if is_valid:
                contact = Contact(
                    contact_list_id=list_id,
                    email=email,
                    first_name=row.get(first_name_col),
                    last_name=row.get(last_name_col),
                    attributes=row
                )
                db.add(contact)
                imported += 1
        
        await db.commit()
        print(f"Successfully imported {imported} contacts with flexible mapping")
        
        # Verify
        from sqlalchemy import select
        res = await db.execute(select(Contact).where(Contact.contact_list_id == list_id))
        contacts = res.scalars().all()
        assert len(contacts) == 2
        assert contacts[0].first_name == "John"
        assert contacts[1].last_name == "Smith"
        print("Verification PASSED!")

if __name__ == "__main__":
    asyncio.run(test_csv_mapping())
