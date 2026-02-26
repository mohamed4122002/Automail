import sys
import os
import asyncio
from uuid import uuid4

# Ensure backend matches the path structure
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.tasks import send_email_task
from backend.models import EmailSend, User, Campaign, EmailTemplate
from backend.core.db import task_context

async def create_test_data():
    async with task_context() as db:
        # 1. Create dummy user
        user_id = uuid4()
        user = User(
            id=user_id,
            email="test_worker_debug@example.com",
            hashed_password="N/A",
            is_active=True
        )
        db.add(user)
        
        # 2. Create dummy campaign
        campaign_id = uuid4()
        campaign = Campaign(id=campaign_id, name="Worker Debug Campaign", owner_id=user_id)
        db.add(campaign)
        
        # 3. Create dummy template
        template_id = uuid4()
        template = EmailTemplate(
            id=template_id, 
            name="Debug Template", 
            subject="Worker Test", 
            html_body="<h1>It Works!</h1>"
        )
        db.add(template)
        
        # 4. Create EmailSend
        email_send = EmailSend(
            user_id=user_id,
            campaign_id=campaign_id,
            template_id=template_id,
            to_email="test_worker_debug@example.com",
            status="queued"
        )
        db.add(email_send)
        await db.commit()
        await db.refresh(email_send)
        
        print(f"Created EmailSend with ID: {email_send.id}")
        return str(email_send.id)

if __name__ == "__main__":
    # Create data in AsyncIO loop
    from backend.core.async_runner import run_async
    try:
        email_send_id = run_async(create_test_data())
        
        print(f"Dispatching send_email_task({email_send_id})...")
        result = send_email_task.delay(email_send_id)
        print(f"Task dispatched! Task ID: {result.id}")
        print("Check worker logs to see if it picked up.")
    except Exception as e:
        print(f"Failed to setup test data: {e}")
