"""
Quick diagnostic script to check campaign data.
"""
import asyncio
from backend.db import AsyncSessionLocal
from backend.models import Campaign, Contact, Workflow, WorkflowNode
from sqlalchemy import select, func
from uuid import UUID

async def diagnose():
    campaign_id = "27a2ee62-ccbf-42e3-8a92-e1fe58b393da"
    
    async with AsyncSessionLocal() as db:
        # Get campaign
        result = await db.execute(
            select(Campaign).where(Campaign.id == UUID(campaign_id))
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            print(f"❌ Campaign {campaign_id} not found!")
            return
        
        print(f"✓ Campaign: {campaign.name}")
        print(f"  Status: {campaign.status}")
        print(f"  Contact List ID: {campaign.contact_list_id}")
        
        # Check contact list
        if campaign.contact_list_id:
            result = await db.execute(
                select(func.count(Contact.id)).where(
                    Contact.contact_list_id == campaign.contact_list_id
                )
            )
            contact_count = result.scalar_one()
            print(f"  Contacts in list: {contact_count}")
        else:
            print(f"  ⚠️  NO CONTACT LIST ASSIGNED!")
        
        # Check workflow
        result = await db.execute(
            select(Workflow).where(Workflow.campaign_id == campaign.id)
        )
        workflow = result.scalar_one_or_none()
        
        if workflow:
            print(f"✓ Workflow: {workflow.name}")
            
            # Check nodes
            result = await db.execute(
                select(func.count(WorkflowNode.id)).where(
                    WorkflowNode.workflow_id == workflow.id
                )
            )
            node_count = result.scalar_one()
            print(f"  Nodes: {node_count}")
        else:
            print(f"  ⚠️  NO WORKFLOW FOUND!")

if __name__ == "__main__":
    asyncio.run(diagnose())
