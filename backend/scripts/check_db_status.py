import asyncio
from backend.db import AsyncSessionLocal
from backend.models import WorkflowInstance, EmailSend, WorkflowStep
from sqlalchemy import select, func

async def check_status():
    async with AsyncSessionLocal() as db:
        # Count workflow instances
        wi_result = await db.execute(select(func.count(WorkflowInstance.id)))
        wi_count = wi_result.scalar_one()
        
        # Count email sends
        es_result = await db.execute(select(func.count(EmailSend.id)))
        es_count = es_result.scalar_one()
        
        # Count workflow steps
        ws_result = await db.execute(select(func.count(WorkflowStep.id)))
        ws_count = ws_result.scalar_one()
        
        # Get recent workflow instances
        wi_query = await db.execute(
            select(WorkflowInstance).order_by(WorkflowInstance.created_at.desc()).limit(5)
        )
        instances = wi_query.scalars().all()
        
        # Get recent email sends
        es_query = await db.execute(
            select(EmailSend).order_by(EmailSend.created_at.desc()).limit(5)
        )
        emails = es_query.scalars().all()
        
        print(f"=== DATABASE STATUS ===")
        print(f"Total WorkflowInstances: {wi_count}")
        print(f"Total EmailSends: {es_count}")
        print(f"Total WorkflowSteps: {ws_count}")
        print(f"\nRecent Workflow Instances:")
        for inst in instances:
            print(f"  - {inst.id}: status={inst.status}, created={inst.created_at}")
        
        print(f"\nRecent Email Sends:")
        for email in emails:
            print(f"  - {email.id}: to={email.to_email}, status={email.status}, created={email.created_at}")

if __name__ == "__main__":
    asyncio.run(check_status())
