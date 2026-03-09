import asyncio
import sys
import os

# Add the project root to sys.path to allow importing the 'backend' package
sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.models import WorkflowInstance, EmailSend, WorkflowStep

async def check_status():
    await init_db()
    try:
        # Count workflow instances
        wi_count = await WorkflowInstance.count()
        
        # Count email sends
        es_count = await EmailSend.count()
        
        # Count workflow steps
        ws_count = await WorkflowStep.count()
        
        # Get recent workflow instances
        instances = await WorkflowInstance.find_all().sort("-created_at").limit(5).to_list()
        
        # Get recent email sends
        emails = await EmailSend.find_all().sort("-created_at").limit(5).to_list()
        
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
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(check_status())
