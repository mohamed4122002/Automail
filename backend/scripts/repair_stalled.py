import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.db import ASYNC_DATABASE_URL
from backend.models import WorkflowInstance, WorkflowStep, WorkflowNode
from backend.tasks import advance_workflow_task
from uuid import UUID
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def repair_stalled():
    engine = create_async_engine(ASYNC_DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with session_factory() as db:
        print("\n--- REPAIRING STALLED INSTANCES ---")
        
        # Find instances that are "running"
        q = await db.execute(
            sa.select(WorkflowInstance).where(WorkflowInstance.status == "running")
        )
        instances = q.scalars().all()
        
        repaired_count = 0
        for i in instances:
            # Find the last completed or running step
            steps_q = await db.execute(
                sa.select(WorkflowStep)
                .where(WorkflowStep.instance_id == i.id)
                .order_by(WorkflowStep.started_at.desc())
            )
            steps = steps_q.scalars().all()
            
            if not steps:
                print(f"Instance {i.id}: No steps. Re-triggering from START.")
                advance_workflow_task.delay(str(i.id), None)
                repaired_count += 1
                continue
            
            last_step = steps[0]
            # Fetch node type for logging
            n_q = await db.execute(sa.select(WorkflowNode).where(WorkflowNode.id == last_step.node_id))
            node = n_q.scalar_one_or_none()
            node_type = node.type if node else "unknown"

            if last_step.status == "completed":
                print(f"Instance {i.id}: Stuck after {node_type} ({last_step.node_id}). ADVANCING...")
                advance_workflow_task.delay(str(i.id), str(last_step.node_id))
                repaired_count += 1
            elif last_step.status == "running" or last_step.status == "pending":
                print(f"Instance {i.id}: Resetting {last_step.status} step {last_step.id} ({node_type}). RE-TRIGGERING...")
                last_step.status = "failed" # Kill the hung one
                await db.commit()
                # Re-trigger the same node
                advance_workflow_task.delay(str(i.id), str(node.id) if node else None)
                repaired_count += 1

        print(f"\nSuccessfully re-queued and repaired {repaired_count} instances.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(repair_stalled())
