import sys
import os
import asyncio
from uuid import uuid4

# Ensure backend matches the path structure
sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.models import EmailSend, User, Campaign, EmailTemplate, UserRole
from backend.tasks import send_email_task

async def create_test_data():
    try:
        await init_db()
        
        # 1. Create dummy user
        user_id = uuid4()
        user = User(
            id=user_id,
            email=f"debug_{uuid4().hex[:6]}@example.com",
            hashed_password="N/A",
            is_active=True,
            role=UserRole.ADMIN
        )
        await user.insert()
        
        # 2. Create dummy campaign
        campaign_id = uuid4()
        campaign = Campaign(id=campaign_id, name="Worker Debug Campaign", owner_id=user_id)
        await campaign.insert()
        
        # 3. Create dummy template
        template_id = uuid4()
        template = EmailTemplate(
            id=template_id, 
            name=f"Debug Template {uuid4().hex[:6]}", 
            subject="Worker Test", 
            html_body="<h1>It Works!</h1>"
        )
        await template.insert()
        
        # 4. Create EmailSend
        email_send = EmailSend(
            user_id=user_id,
            campaign_id=campaign_id,
            template_id=template_id,
            to_email="test_worker_debug@example.com",
            status="queued"
        )
        await email_send.insert()
        
        print(f"Created EmailSend with ID: {email_send.id}")
        return str(email_send.id)
    finally:
        await close_db()

async def main():
    try:
        email_send_id = await create_test_data()
        
        print(f"Dispatching send_email_task({email_send_id})...")
        result = send_email_task.delay(email_send_id)
        print(f"Task dispatched! Task ID: {result.id}")
        print("Check worker logs to see if it picked up.")
    except Exception as e:
        print(f"Failed to setup test data: {e}")

if __name__ == "__main__":
    asyncio.run(main())
