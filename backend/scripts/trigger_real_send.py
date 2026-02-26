import asyncio
import uuid
from backend.db import AsyncSessionLocal
from backend.models import User, Campaign, EmailSend, EmailTemplate, WorkflowNode, Workflow
from backend.tasks import send_email_task
from sqlalchemy import select

async def trigger_real_send():
    async with AsyncSessionLocal() as db:
        # Find a user to send to
        res_user = await db.execute(select(User).limit(1))
        user = res_user.scalar_one_or_none()
        
        # Find a campaign
        res_campaign = await db.execute(select(Campaign).limit(1))
        campaign = res_campaign.scalar_one_or_none()
        
        if not user or not campaign:
            print("Need at least one user and one campaign in DB")
            return
            
        # Find a template
        res_template = await db.execute(select(EmailTemplate).limit(1))
        template = res_template.scalar_one_or_none()
        
        if not template:
            print("Need an email template")
            return
            
        # Create EmailSend record
        email_send = EmailSend(
            user_id=user.id,
            campaign_id=campaign.id,
            template_id=template.id,
            to_email="fatma.e@marketeersresearch.com", # As in user logs
            status="pending",
            unsubscribe_token=str(uuid.uuid4())
        )
        db.add(email_send)
        await db.commit()
        await db.refresh(email_send)
        
        print(f"Created EmailSend {email_send.id}")
        print(f"Queuing send_email_task for {email_send.id}...")
        
        # Queue the task
        task_id = send_email_task.apply_async(args=[str(email_send.id)])
        print(f"Task queued with ID: {task_id}")
        print("Now watch the worker logs for 'Provider: SMTPProvider' and 'SMTP email SENT successfully'")

if __name__ == "__main__":
    asyncio.run(trigger_real_send())
