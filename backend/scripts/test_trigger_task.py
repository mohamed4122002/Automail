#!/usr/bin/env python
"""Test script to manually trigger a workflow task."""
import asyncio
import uuid
from backend.db import AsyncSessionLocal
from backend.models import WorkflowInstance
from backend.tasks import advance_workflow_task
from sqlalchemy import select

async def test_trigger():
    """Find a workflow instance and trigger its task."""
    async with AsyncSessionLocal() as db:
        # Get the first workflow instance
        result = await db.execute(
            select(WorkflowInstance)
            .where(WorkflowInstance.status == "running")
            .limit(1)
        )
        instance = result.scalar_one_or_none()
        
        if not instance:
            print("No running workflow instances found")
            return
        
        print(f"Found instance: {instance.id}")
        print(f"Triggering advance_workflow_task for instance {instance.id}")
        
        # Queue the task
        result = advance_workflow_task.delay(str(instance.id), None)
        print(f"Task queued with ID: {result.id}")
        print("Check Celery worker logs to see if it processes the task")

if __name__ == "__main__":
    asyncio.run(test_trigger())
