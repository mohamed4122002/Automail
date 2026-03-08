from fastapi import APIRouter
from uuid import UUID
from ..services.workflow_engine import WorkflowEngineService

router = APIRouter(prefix="/workflow-runtime", tags=["workflow-runtime"])

@router.post("/instances/{id}/run-step")
async def run_step(
    id: UUID, 
    node_id: UUID | None = None
):
    # This endpoint is primarily for testing manual triggers or debugging
    # Real execution happens via Celery
    from ..tasks import advance_workflow_task
    advance_workflow_task.delay(str(id), str(node_id) if node_id else None)
    return {"status": "queued", "instance_id": id}

@router.get("/instances/{id}/data")
async def get_instance_data(id: UUID):
    service = WorkflowEngineService()
    return await service.get_instance_data(id)

@router.get("/instances/{id}/snapshots")
async def get_instance_snapshots(id: UUID):
    service = WorkflowEngineService()
    return await service.get_instance_snapshots(id)
