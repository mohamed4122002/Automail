import asyncio
from backend.db import AsyncSessionLocal
from backend.models import Campaign, Workflow, WorkflowNode, EmailSend
from sqlalchemy import select, func
from uuid import UUID

async def check_campaign_details():
    campaign_id = UUID('27a2ee62-ccbf-42e3-8a92-e1fe58b393da')
    
    async with AsyncSessionLocal() as db:
        # Get campaign
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            print("❌ Campaign not found!")
            return
        
        print(f"✓ Campaign: {campaign.name}")
        
        # Get workflow
        result = await db.execute(
            select(Workflow).where(Workflow.campaign_id == campaign_id)
        )
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            print("❌ No workflow found!")
            return
        
        print(f"✓ Workflow: {workflow.name} (ID: {workflow.id})")
        
        # Get workflow nodes
        result = await db.execute(
            select(WorkflowNode.type, func.count(WorkflowNode.id))
            .where(WorkflowNode.workflow_id == workflow.id)
            .group_by(WorkflowNode.type)
        )
        nodes = result.all()
        print("\n  Workflow Nodes:")
        if nodes:
            for node_type, count in nodes:
                print(f"    {node_type}: {count}")
        else:
            print("    ⚠️  NO NODES FOUND!")
        
        # Get email sends for this campaign
        result = await db.execute(
            select(EmailSend.status, func.count(EmailSend.id))
            .where(EmailSend.campaign_id == campaign_id)
            .group_by(EmailSend.status)
        )
        emails = result.all()
        print("\n  Email Sends:")
        if emails:
            for status, count in emails:
                print(f"    {status}: {count}")
        else:
            print("    ⚠️  NO EMAILS FOUND!")

if __name__ == "__main__":
    asyncio.run(check_campaign_details())
