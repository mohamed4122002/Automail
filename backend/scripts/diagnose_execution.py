
import asyncio
import uuid
from sqlalchemy import select
from backend.db import AsyncSessionLocal
from backend.models import Campaign, Workflow, WorkflowNode, WorkflowInstance, WorkflowStep, EmailSend

async def diagnose_execution(campaign_id_str=None):
    async with AsyncSessionLocal() as db:
        if campaign_id_str:
            campaign_id = uuid.UUID(campaign_id_str)
            res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        else:
            # Pick the most recent campaign
            res = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()).limit(1))
            
        campaign = res.scalar_one_or_none()
        if not campaign:
            print(f"No campaign found")
            return

        campaign_id = campaign.id
        print(f"--- Campaign Diagnostic ---")
        print(f"Campaign: {campaign.name} (ID: {campaign.id})")
        print(f"Status: {'Active' if campaign.is_active else 'Paused'}")
        print(f"Created At: {campaign.created_at}")

        # Check workflow
        res = await db.execute(select(Workflow).where(Workflow.campaign_id == campaign_id))
        workflow = res.scalar_one_or_none()
        if not workflow:
            print("No workflow found for this campaign")
            return
        
        print(f"Workflow: {workflow.name} (ID: {workflow.id})")

        # Check nodes
        res = await db.execute(select(WorkflowNode).where(WorkflowNode.workflow_id == workflow.id))
        nodes = res.scalars().all()
        print(f"Nodes ({len(nodes)}):")
        for n in nodes:
            print(f"  - {n.type.upper()}: {n.id}")

        # Check instances
        res = await db.execute(select(WorkflowInstance).where(WorkflowInstance.workflow_id == workflow.id))
        instances = res.scalars().all()
        print(f"Instances ({len(instances)}):")
        for inst in instances:
            # Check most recent step
            res_step = await db.execute(
                select(WorkflowStep)
                .where(WorkflowStep.instance_id == inst.id)
                .order_by(WorkflowStep.created_at.desc())
                .limit(1)
            )
            step = res_step.scalar_one_or_none()
            if step:
                timing = f"{step.started_at} -> {step.finished_at}" if step.started_at else "Not started"
                step_info = f"Last step: {step.status} at node {step.node_id} ({timing})"
            else:
                step_info = "No steps recorded"
            print(f"  - User ID: {inst.user_id}, status: {inst.status}. {step_info}")

        # Check email sends
        res = await db.execute(select(EmailSend).where(EmailSend.campaign_id == campaign_id))
        emails = res.scalars().all()
        print(f"Email Sends ({len(emails)}):")
        for e in emails:
            print(f"  - To: {e.to_email}, status: {e.status}, created: {e.created_at}")

if __name__ == "__main__":
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(diagnose_execution(cid))
