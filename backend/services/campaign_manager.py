import logging
from datetime import datetime, timedelta
from uuid import UUID

from ..models import Campaign, Workflow, WorkflowInstance, Contact, User, Lead, LeadStatusEnum
from ..tasks import advance_workflow_task

logger = logging.getLogger(__name__)

class CampaignManagerService:
    def __init__(self):
        pass

    async def activate_campaign(self, campaign_id: UUID, owner_id: UUID) -> dict:
        from ..api.realtime import broadcast_event
        
        campaign = await Campaign.find_one(Campaign.id == campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        
        if not campaign.contact_list_id:
            raise ValueError("No contact list selected for this campaign")
            
        workflow = await Workflow.find_one(Workflow.campaign_id == campaign_id)
        if not workflow:
            raise ValueError("No workflow associated with this campaign")

        campaign.is_active = True
        await campaign.save()

        await broadcast_event({
            "type": "event",
            "event_type": "campaign_activated",
            "campaign_id": str(campaign_id),
            "campaign_name": campaign.name,
            "timestamp": datetime.utcnow().isoformat()
        })

        contacts = await Contact.find(Contact.contact_list_id == campaign.contact_list_id).to_list()
        
        if not contacts:
            return {"message": "Campaign activated (0 contacts found)", "campaign_id": str(campaign_id)}

        instances_started = 0
        tasks_to_run = []
        
        for contact in contacts:
            task = await self._reconcile_contact_workflow(contact, workflow)
            if task:
                tasks_to_run.append(task)
                instances_started += 1

        if tasks_to_run:
            logger.info(f"Dispatching {len(tasks_to_run)} workflow tasks in parallel")
            from celery import group
            job = group(tasks_to_run)
            job.apply_async()

        return {
            "message": "Campaign activated successfully",
            "campaign_id": str(campaign_id),
            "contacts_processed": len(contacts),
            "instances_started": instances_started,
            "tasks_dispatched": len(tasks_to_run)
        }

    async def _reconcile_contact_workflow(self, contact: Contact, workflow: Workflow):
        user = await self._ensure_shadow_user(contact)
        await self._ensure_lead(contact)
        
        instance = await WorkflowInstance.find_one(
            WorkflowInstance.workflow_id == workflow.id,
            WorkflowInstance.user_id == user.id
        )
        
        if not instance:
            instance = WorkflowInstance(
                workflow_id=workflow.id,
                user_id=user.id,
                status="pending"
            )
            await instance.insert()
            return advance_workflow_task.s(str(instance.id), None)

        if instance.status == "pending":
            return advance_workflow_task.s(str(instance.id), None)

        if instance.status == "running":
            if getattr(instance, 'updated_at', datetime.utcnow()) < (datetime.utcnow() - timedelta(minutes=15)):
                logger.warning(f"Recovering stale instance {instance.id}")
                return advance_workflow_task.s(str(instance.id), None)
            return None

        if instance.status in ["completed", "failed", "terminated"]:
            logger.info(f"Restarting terminal instance {instance.id}")
            instance.status = "pending"
            instance.updated_at = datetime.utcnow()
            await instance.save()
            return advance_workflow_task.s(str(instance.id), None)

        return None

    async def _ensure_shadow_user(self, contact: Contact) -> User:
        user = await User.find_one(User.email == contact.email)
        if not user:
            user = User(
                email=contact.email,
                hashed_password="N/A",
                first_name=contact.first_name,
                last_name=contact.last_name,
                is_active=False
            )
            await user.insert()
        return user

    async def _ensure_lead(self, contact: Contact) -> Lead:
        lead = await Lead.find_one(Lead.contact_id == contact.id)
        if not lead:
            lead = Lead(
                contact_id=contact.id,
                lead_status=LeadStatusEnum.new,
                lead_score=0
            )
            await lead.insert()
        return lead

    async def pause_campaign(self, campaign_id: UUID) -> dict:
        from ..api.realtime import broadcast_event
        campaign = await Campaign.find_one(Campaign.id == campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        
        campaign.is_active = False
        await campaign.save()
        
        await broadcast_event({
            "type": "event",
            "event_type": "campaign_paused",
            "campaign_id": str(campaign_id),
            "campaign_name": campaign.name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {"message": "Campaign paused", "campaign_id": str(campaign_id)}

    async def update_workflow(self, campaign_id: UUID, new_workflow_id: UUID) -> dict:
        from ..api.realtime import broadcast_event
        
        campaign = await Campaign.find_one(Campaign.id == campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")

        new_workflow = await Workflow.find_one(Workflow.id == new_workflow_id)
        if not new_workflow:
            raise ValueError("New workflow not found")

        # Unlink existing workflows for this campaign
        old_workflows = await Workflow.find(Workflow.campaign_id == campaign_id).to_list()
        for wf in old_workflows:
            wf.campaign_id = None
            await wf.save()

        new_workflow.campaign_id = campaign_id
        await new_workflow.save()

        await broadcast_event({
            "type": "event",
            "event_type": "campaign_config_updated",
            "campaign_id": str(campaign_id),
            "campaign_name": campaign.name,
            "detail": f"Workflow swapped to '{new_workflow.name}'",
            "timestamp": datetime.utcnow().isoformat()
        })

        return {
            "message": "Workflow updated successfully",
            "campaign_id": str(campaign_id),
            "workflow_id": str(new_workflow_id),
            "workflow_name": new_workflow.name
        }

    async def get_workflow_health(self) -> dict:
        instances = await WorkflowInstance.find_all().to_list()
        stats = {}
        stalled_count = 0
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        for i in instances:
            stats[i.status] = stats.get(i.status, 0) + 1
            if i.status == "running" and getattr(i, 'updated_at', datetime.utcnow()) < hour_ago:
                stalled_count += 1
                
        return {
            "stats": stats,
            "stalled_count": stalled_count,
            "is_healthy": stalled_count == 0
        }

    async def repair_stalled_instances(self) -> dict:
        from ..tasks import advance_workflow_task
        from ..models import WorkflowStep
        
        running_instances = await WorkflowInstance.find(WorkflowInstance.status == "running").to_list()
        
        repaired = 0
        for i in running_instances:
            steps = await WorkflowStep.find(WorkflowStep.instance_id == i.id).sort("-started_at").to_list()
            
            if not steps:
                advance_workflow_task.delay(str(i.id), None)
                repaired += 1
                continue
            
            last_step = steps[0]
            if last_step.status == "completed":
                advance_workflow_task.delay(str(i.id), str(last_step.node_id))
                repaired += 1
            elif last_step.status in ["running", "pending"]:
                if getattr(last_step, 'started_at', datetime.utcnow()) < (datetime.utcnow() - timedelta(minutes=15)):
                    last_step.status = "failed"
                    await last_step.save()
                    advance_workflow_task.delay(str(i.id), str(last_step.node_id))
                    repaired += 1
                    
        return {"repaired_count": repaired}
