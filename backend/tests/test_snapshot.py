import asyncio
import uuid
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from backend.models import User, Workflow, WorkflowInstance, WorkflowNode, WorkflowStep, WorkflowInstanceData, WorkflowSnapshot
from backend.config import settings
from datetime import datetime

async def verify_snapshot():
    # Force asyncpg for the test
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Setup mock data
        user_res = await db.execute(select(User).limit(1))
        user = user_res.scalar_one_or_none()
        if not user:
            print("No user found")
            return

        workflow_name = f"Snapshot Test {uuid.uuid4().hex[:8]}"
        workflow = Workflow(name=workflow_name)
        db.add(workflow)
        await db.flush()

        node = WorkflowNode(
            workflow_id=workflow.id,
            type="condition",
            config={"condition": {"type": "event_check", "event": "opened", "within_hours": 24}}
        )
        db.add(node)
        await db.flush()

        instance = WorkflowInstance(workflow_id=workflow.id, user_id=user.id)
        db.add(instance)
        await db.flush()

        # Set some instance data
        instance_data = WorkflowInstanceData(instance_id=instance.id, data={"test_key": "test_value"})
        db.add(instance_data)
        await db.flush()

        step = WorkflowStep(instance_id=instance.id, node_id=node.id, status="pending")
        db.add(step)
        await db.commit()

        print(f"Triggering evaluate_condition_task for instance {instance.id}...")
        
        # 2. Run the task logic (mocking Celery call)
        # Since evaluate_condition_task calls asyncio.run(), we must run it in a separate thread
        import threading
        from backend.tasks import evaluate_condition_task
        
        task_thread = threading.Thread(
            target=evaluate_condition_task, 
            args=(str(instance.id), str(node.id), str(step.id))
        )
        task_thread.start()
        task_thread.join()

        # 3. Verify snapshot
        await db.refresh(instance)
        result = await db.execute(
            select(WorkflowSnapshot).where(WorkflowSnapshot.instance_id == instance.id)
        )
        snapshot = result.scalar_one_or_none()
        
        if snapshot:
            print("SUCCESS: Snapshot created!")
            print(f"Data: {json.dumps(snapshot.data_snapshot, indent=2)}")
            print(f"Result: {json.dumps(snapshot.condition_result, indent=2)}")
        else:
            print("FAILURE: No snapshot found.")

if __name__ == "__main__":
    asyncio.run(verify_snapshot())
