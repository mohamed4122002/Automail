import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.db import ASYNC_DATABASE_URL
from backend.models import (
    Campaign, 
    Workflow, 
    WorkflowNode, 
    WorkflowEdge, 
    WorkflowInstance, 
    WorkflowStep, 
    EmailSend, 
    Event, 
    User, 
    ContactList
)
from uuid import UUID
import logging
from redis import Redis
from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def diagnose_campaigns():
    engine = create_async_engine(ASYNC_DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    # Check Redis Queue
    try:
        redis = Redis.from_url(settings.REDIS_URL)
        queue_len = redis.llen("celery")
        print(f"\n--- REDIS / CELERY QUEUE ---")
        print(f"Queue 'celery' length: {queue_len}")
    except Exception as e:
        print(f"Failed to check Redis: {e}")

    async with session_factory() as db:
        print("\n--- ACTIVE CAMPAIGNS & WORKFLOWS ---")
        q = await db.execute(
            sa.select(Campaign)
            .where(Campaign.is_active == True)
            .options(sa.orm.selectinload(Campaign.workflow).selectinload(Workflow.nodes))
        )
        campaigns = q.scalars().all()
        for c in campaigns:
            print(f"Campaign: {c.name} ({c.id})")
            if c.workflow:
                print(f"  Workflow: {c.workflow.name} ({c.workflow.id})")
                for node in c.workflow.nodes:
                    print(f"    Node: {node.type} ({node.id}) | Config: {node.config}")
            else:
                print(f"  ⚠️ NO WORKFLOW LINKED")
        
        print("\n--- WORKFLOW INSTANCE STATUS ---")
        # Count statuses
        q_stats = await db.execute(
            sa.select(WorkflowInstance.status, sa.func.count(WorkflowInstance.id))
            .group_by(WorkflowInstance.status)
        )
        for status, count in q_stats.all():
            print(f"Status '{status}': {count} instances")

        print("\n--- SAMPLE STALLED INSTANCES (running but no progress today) ---")
        q = await db.execute(
            sa.select(WorkflowInstance)
            .where(WorkflowInstance.status == "running")
            .options(
                sa.orm.selectinload(WorkflowInstance.workflow).selectinload(Workflow.campaign)
            )
            .limit(10)
        )
        instances = q.scalars().all()
        for i in instances:
            steps_q = await db.execute(sa.select(WorkflowStep).where(WorkflowStep.instance_id == i.id).order_by(WorkflowStep.started_at.desc()))
            steps = steps_q.scalars().all()
            last_step = steps[0] if steps else None
            node_type = "N/A"
            campaign_name = i.workflow.campaign.name if i.workflow and i.workflow.campaign else "N/A"
            if last_step:
                n_q = await db.execute(sa.select(WorkflowNode).where(WorkflowNode.id == last_step.node_id))
                node = n_q.scalar_one_or_none()
                node_type = node.type if node else "N/A"
            
            print(f"ID: {i.id} | Campaign: {campaign_name} | Node Type: {node_type} | Last Step St: {last_step.status if last_step else 'N/A'} | Updated: {i.updated_at}")

        print("\n--- EMAIL SENDS (LAST 10) ---")
        q = await db.execute(sa.select(EmailSend).order_by(EmailSend.created_at.desc()).limit(10))
        sends = q.scalars().all()
        for s in sends:
            print(f"ID: {s.id} | To: {s.to_email} | Status: {s.status} | Created: {s.created_at}")

        print("\n--- RECENT EVENTS (LAST 10) ---")
        q = await db.execute(sa.select(Event).order_by(Event.created_at.desc()).limit(10))
        events = q.scalars().all()
        for e in events:
            print(f"Time: {e.created_at} | Type: {e.type} | Campaign ID: {e.campaign_id}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(diagnose_campaigns())
