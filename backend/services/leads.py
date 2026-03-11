from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from ..models import Lead, User, LeadNote, CRMLeadStage, CRMActivity, ActivityType, CRMTask, TaskStatus
from ..schemas.leads import LeadUpdate
from ..signals import CRMSignals
from ..cache import delete_cache

class LeadService:
    # Existing methods...
    @staticmethod
    async def get_lead_with_details(lead_id: UUID) -> Optional[dict]:
        lead = await Lead.find_one(Lead.id == lead_id)
        if not lead:
            return None
            
        # Fetch related users
        assigned_to = await User.find_one(User.id == lead.assigned_to_id) if lead.assigned_to_id else None
        assigned_by = await User.find_one(User.id == lead.assigned_by_id) if lead.assigned_by_id else None
        
        return {
            "lead": lead,
            "assigned_to": assigned_to,
            "assigned_by": assigned_by
        }

    @staticmethod
    async def update_lead_stage(lead_id: UUID, new_stage: CRMLeadStage, user_id: UUID) -> Lead:
        lead = await Lead.find_one(Lead.id == lead_id)
        if not lead:
            raise ValueError("Lead not found")
        
        old_stage = lead.stage
        if old_stage == new_stage:
            return lead
            
        lead.stage = new_stage
        lead.last_activity_at = datetime.now(timezone.utc)
        lead.updated_at = datetime.now(timezone.utc)
        
        await lead.save()
        
        # Log system note as activity
        await LeadService.log_activity(
            lead_id=lead_id,
            user_id=user_id,
            activity_type=ActivityType.SYSTEM,
            content=f"Stage changed from {old_stage} to {new_stage}"
        )

        # Broadcast signal
        CRMSignals.broadcast_lead_update(
            lead_id=lead_id, 
            user_id=user_id, 
            change_type="stage_transition",
            data={"from": str(old_stage), "to": str(new_stage)}
        )

        # Bust cached stats so next request reflects the new stage
        await delete_cache("leads:stats")
        await delete_cache("leads:pipeline_summary")
        await delete_cache("analytics:dashboard:*")

        return lead

    @staticmethod
    async def assign_lead(lead_id: UUID, assigned_to_id: UUID, assigned_by_id: UUID, assignment_type: str = "manual") -> Lead:
        lead = await Lead.find_one(Lead.id == lead_id)
        if not lead:
            raise ValueError("Lead not found")
            
        assignee = await User.find_one(User.id == assigned_to_id)
        if not assignee:
            raise ValueError("Assignee not found")
            
        lead.assigned_to_id = assigned_to_id
        lead.assigned_by_id = assigned_by_id
        lead.assigned_at = datetime.now(timezone.utc)
        lead.assignment_type = assignment_type
        lead.claimed_at = datetime.now(timezone.utc)
        lead.last_activity_at = datetime.now(timezone.utc)
        
        await lead.save()
        
        # Log system note as activity
        await LeadService.log_activity(
            lead_id=lead_id,
            user_id=assigned_by_id,
            activity_type=ActivityType.SYSTEM,
            content=f"Lead assigned to {assignee.email} (Type: {assignment_type})"
        )
        
        return lead

    @staticmethod
    async def log_activity(
        lead_id: UUID, 
        user_id: Optional[UUID], 
        activity_type: ActivityType, 
        content: str, 
        metadata: Optional[dict] = None
    ) -> CRMActivity:
        activity = CRMActivity(
            lead_id=lead_id,
            user_id=user_id,
            type=activity_type,
            content=content,
            metadata=metadata or {}
        )
        await activity.insert()
        
        # Update lead last_activity_at
        lead = await Lead.find_one(Lead.id == lead_id)
        if lead:
            lead.last_activity_at = datetime.now(timezone.utc)
            await lead.save()
            
            # Broadcast activity signal
            if user_id:
                CRMSignals.broadcast_activity_update(lead.id, user_id, activity_type.value if hasattr(activity_type, 'value') else activity_type)
            
        return activity

    @staticmethod
    async def create_task(
        lead_id: UUID,
        assigned_to_id: Optional[UUID],
        title: str,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> CRMTask:
        task = CRMTask(
            lead_id=lead_id,
            assigned_to_id=assigned_to_id,
            title=title,
            description=description,
            due_date=due_date
        )
        await task.insert()
        return task

    @staticmethod
    async def get_tasks(lead_id: UUID, status: Optional[TaskStatus] = None) -> List[CRMTask]:
        query = {"lead_id": lead_id}
        if status:
            query["status"] = status
        return await CRMTask.find(query).sort("+due_date").to_list()

    @staticmethod
    async def update_task_status(task_id: UUID, status: TaskStatus, user_id: UUID) -> CRMTask:
        task = await CRMTask.find_one(CRMTask.id == task_id)
        if not task:
            raise ValueError("Task not found")
            
        task.status = status
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)
        
        task.updated_at = datetime.now(timezone.utc)
        await task.save()
        
        # Log activity for task completion/update
        await LeadService.log_activity(
            lead_id=task.lead_id,
            user_id=user_id,
            activity_type=ActivityType.SYSTEM,
            content=f"Task '{task.title}' updated to {status}"
        )

        # Broadcast task signal
        CRMSignals.broadcast_task_update(task.lead_id, task.id, user_id, f"status_{status}")
        
        return task
