from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from uuid import UUID
from ..models import WorkflowInstance, WorkflowInstanceData
from ..schemas.base import BaseResponse # Placeholder import

class WorkflowEngineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_instance_data(self, instance_id: UUID) -> dict:
        query = sa.select(WorkflowInstanceData).where(WorkflowInstanceData.instance_id == instance_id)
        result = await self.db.execute(query)
        data_obj = result.scalar_one_or_none()
        return data_obj.data if data_obj else {}

    async def update_instance_data(self, instance_id: UUID, updates: dict):
        """
        Atomically merges updates into WorkflowInstanceData.data using 
        the PostgreSQL '||' JSONB operator to prevent race conditions.
        """
        # 1. Try to update existing record atomically
        # The '||' operator performs a top-level merge of two JSONB objects.
        stmt = (
            sa.update(WorkflowInstanceData)
            .where(WorkflowInstanceData.instance_id == instance_id)
            .values(data=sa.func.coalesce(WorkflowInstanceData.data, sa.text("'{}'::jsonb")) + sa.bindparam('updates', type_=sa.JSON))
            .returning(WorkflowInstanceData.data)
        )
        
        result = await self.db.execute(stmt, {"updates": updates})
        updated_data = result.scalar_one_or_none()
        
        if updated_data is not None:
            await self.db.commit()
            return updated_data
            
        # 2. If no record was updated, create it
        # We use a flush/commit pattern here. 
        # In a high-concurrency race to insert, standard DB unique constraints will catch the error.
        try:
            data_obj = WorkflowInstanceData(instance_id=instance_id, data=updates)
            self.db.add(data_obj)
            await self.db.commit()
            return updates
        except sa.exc.IntegrityError:
            # Another task inserted it just now; retry the atomic update once
            await self.db.rollback()
            # Re-fetch it after conflict
            result = await self.db.execute(stmt, {"updates": updates})
            updated_data = result.scalar_one()
            await self.db.commit()
            return updated_data

    async def get_instance_snapshots(self, instance_id: UUID) -> list:
        from ..models import WorkflowSnapshot
        query = (
            sa.select(WorkflowSnapshot)
            .where(WorkflowSnapshot.instance_id == instance_id)
            .order_by(WorkflowSnapshot.created_at.asc())
        )
        result = await self.db.execute(query)
        snapshots = result.scalars().all()
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
