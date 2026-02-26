import asyncio
from backend.db import AsyncSessionLocal
from backend.models import EmailSend
from backend.tasks import send_email_task
from sqlalchemy import select, func

async def requeue_stuck_emails():
    async with AsyncSessionLocal() as db:
        print("Searching for stuck 'queued' emails...")
        
        # Find emails that are 'queued' but not processed
        result = await db.execute(
            select(EmailSend).where(EmailSend.status == 'queued')
        )
        stuck_emails = result.scalars().all()
        
        if not stuck_emails:
            print("✅ No stuck emails found.")
            return

        print(f"⚠️ Found {len(stuck_emails)} stuck emails. Re-queuing them now...")
        
        count = 0
        for email in stuck_emails:
            # Dispatch task
            send_email_task.delay(str(email.id))
            count += 1
            
            if count % 10 == 0:
                print(f"    ... {count} processed ...")
        
        print(f"✅ Successfully re-queued {count} emails!")

if __name__ == "__main__":
    asyncio.run(requeue_stuck_emails())
