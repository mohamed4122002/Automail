from uuid import UUID
from datetime import datetime

class WorkflowEngineService:
    def __init__(self):
        pass

    async def get_instance_data(self, instance_id: UUID) -> dict:
        from ..models import WorkflowInstanceData
        data_obj = await WorkflowInstanceData.find_one(WorkflowInstanceData.instance_id == instance_id)
        return data_obj.data if data_obj else {}

    async def update_instance_data(self, instance_id: UUID, updates: dict):
        """
        Merge updates into WorkflowInstanceData.data.
        """
        from ..models import WorkflowInstanceData
        data_obj = await WorkflowInstanceData.find_one(WorkflowInstanceData.instance_id == instance_id)
        
        if data_obj:
            # Merge dictionaries
            data_dict = data_obj.data or {}
            data_dict.update(updates)
            data_obj.data = data_dict
            await data_obj.save()
            return data_dict
        else:
            data_obj = WorkflowInstanceData(instance_id=instance_id, data=updates)
            await data_obj.insert()
            return updates

    async def get_instance_snapshots(self, instance_id: UUID) -> list:
        from ..models import WorkflowSnapshot
        snapshots = await WorkflowSnapshot.find(
            WorkflowSnapshot.instance_id == instance_id
        ).sort("created_at").to_list()
        
        return [
            {
                "id": str(s.id),
                "step_id": str(s.step_id),
                "node_id": str(s.node_id),
                "data_snapshot": s.data_snapshot,
                "condition_result": s.condition_result,
                "created_at": s.created_at.isoformat()
            }
            for s in snapshots
        ]
