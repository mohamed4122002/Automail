from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from ..db import get_db
from ..services.workflow_engine import WorkflowEngineService
from ..schemas.base import BaseResponse

router = APIRouter(prefix="/workflow-runtime", tags=["workflow-runtime"])

@router.post("/instances/{id}/run-step")
async def run_step(
    id: UUID, 
    node_id: UUID | None = None,
    db: AsyncSession = Depends(get_db)
):
    # This endpoint is primarily for testing manual triggers or debugging
    # Real execution happens via Celery
    from ..tasks import advance_workflow_task
    advance_workflow_task.delay(str(id), str(node_id) if node_id else None)
    return {"status": "queued", "instance_id": id}

@router.get("/instances/{id}/data")
async def get_instance_data(id: UUID, db: AsyncSession = Depends(get_db)):
    service = WorkflowEngineService(db)
    return await service.get_instance_data(id)

@router.get("/instances/{id}/snapshots")
async def get_instance_snapshots(id: UUID, db: AsyncSession = Depends(get_db)):
    service = WorkflowEngineService(db)
    return await service.get_instance_snapshots(id)
