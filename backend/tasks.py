from beanie.operators import In
from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import UUID
import asyncio

from .celery_app import celery_app
from .conditions import evaluate_condition
from .email_providers import get_email_provider
import liquid
from .models import (
    Contact,
    ContactList,
    EmailSend,
    EmailTemplate,
    Event,
    Lead,
    LeadStatusEnum,
    User,
    WorkflowEdge,
    WorkflowInstance,
    WorkflowNode,
    WorkflowStep,
    Campaign,
    EmailRetryAttempt,
    WorkflowInstanceData,
    WorkflowSnapshot
)
from .services.spam_shield import spam_shield_service
from .core.async_runner import run_async
from .core.monitoring import task_metrics
import logging

logger = logging.getLogger(__name__)


async def _broadcast_event_to_websocket(
    event_type: str, 
    user_id: str, 
    user_email: str, 
    campaign_id: str = None,
    campaign_name: str = None,
    workflow_id: str = None,
    node_id: str = None
):
    """Helper to broadcast events to WebSocket clients."""
    try:
        from .api.realtime import broadcast_event
        from datetime import datetime
        
        await broadcast_event({
            "type": "event",
            "event_type": event_type,
            "user_id": user_id,
            "user_email": user_email,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "workflow_id": workflow_id,
            "node_id": node_id,
            "timestamp": datetime.utcnow().isoformat(),
            "is_hot_lead": event_type == "clicked"
        })
    except Exception as e:
        # Don't fail the task if WebSocket broadcast fails
        logger.error(f"Failed to broadcast event: {e}")


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
@task_metrics
def send_email_task(self, email_send_id: str) -> None:
    """Celery task to send an email via the configured provider."""

    async def _run() -> None:
        email_send_uuid = UUID(email_send_id) if isinstance(email_send_id, str) else email_send_id
        email_send = await EmailSend.find_one(EmailSend.id == email_send_uuid)
        
        if not email_send:
            logger.error(f"EmailSend {email_send_id} not found")
            return

        if not email_send.template_id:
            return

        template = await EmailTemplate.find_one(EmailTemplate.id == email_send.template_id)
        if not template:
            logger.error(f"Template not found for email_send {email_send_id}")
            return

        logger.info(f"[{email_send_id}] Fetching provider...")
        provider = await get_email_provider() # Modified to not need db arg if possible
        logger.info(f"[{email_send_id}] Provider: {provider.__class__.__name__}")
        
        # A/B Testing Logic
        from .services.ab_testing import ABTestingService
        ab_service = ABTestingService()
        active_test = await ab_service.get_active_test(
            campaign_id=email_send.campaign_id,
            workflow_step_id=email_send.workflow_step_id
        )
        
        subject = template.subject
        if active_test:
            logger.info(f"[{email_send_id}] A/B test active: {active_test.id}")
            active_test.total_sent += 1
            if active_test.status == "active":
                if active_test.total_sent <= active_test.test_limit:
                    variant_letter = "a" if active_test.total_sent % 2 == 1 else "b"
                    email_send.variant_id = active_test.id
                    email_send.variant_letter = variant_letter
                    subject = active_test.subject_a if variant_letter == "a" else active_test.subject_b
                    if active_test.total_sent == active_test.test_limit:
                        await ab_service.select_winner(active_test.id)
                else:
                    if not active_test.winner:
                        active_test.winner = await ab_service.select_winner(active_test.id)
                    subject = active_test.subject_a if active_test.winner == "a" else active_test.subject_b
            else:
                subject = active_test.subject_a if active_test.winner == "a" else active_test.subject_b
                email_send.variant_id = active_test.id
                email_send.variant_letter = active_test.winner
                
            await active_test.save()

        user = await User.find_one(User.id == email_send.user_id)

        from .config import settings
        unsubscribe_link = f"{settings.FRONTEND_URL}/unsubscribe/{str(email_send.unsubscribe_token)}"
        
        user_data = {
            "first_name": user.first_name if user else "there",
            "last_name": user.last_name if user else "",
            "email": email_send.to_email,
            "unsubscribe_link": unsubscribe_link
        }
        
        try:
            liquid_tmpl = liquid.Template(template.html_body)
            rendered_body = liquid_tmpl.render(**user_data)
        except Exception as e:
            logger.error(f"[{email_send_id}] Template render error: {e}")
            rendered_body = template.html_body
        
        if "unsubscribe_link" not in template.html_body:
            rendered_body += f"<br><br><p style='font-size: 12px; color: #666;'>If you wish to stop receiving these emails, you can <a href='{unsubscribe_link}'>unsubscribe here</a>.</p>"
        
        from .services.reputation import ReputationWarmupService
        reputation_service = ReputationWarmupService()
        
        # Check if we can send based on warmup limits
        logger.info(f"[{email_send_id}] Checking warmup limit...")
        can_send = await reputation_service.check_warmup_limit(email_send.campaign_id) if email_send.campaign_id else True
        if not can_send:
            logger.warning(f"[{email_send_id}] Warmup limit reached. Re-scheduling.")
            raise self.retry(countdown=3600 * 24)

        logger.info(f"[{email_send_id}] Calling provider.send_email...")
        message_id = await provider.send_email(
            to_email=email_send.to_email,
            subject=subject,
            html_body=rendered_body,
            unsubscribe_url=unsubscribe_link,
            metadata={"email_send_id": str(email_send.id)},
        )
        logger.info(f"[{email_send_id}] Sent. MsgID: {message_id}")
        
        if email_send.campaign_id:
            await reputation_service.increment_sent_count(email_send.campaign_id)
            
        email_send.status = "sent"
        email_send.provider_message_id = message_id
        email_send.data = {"subject": subject}
        await email_send.save()

        event = Event(
            type="sent",
            user_id=email_send.user_id,
            campaign_id=email_send.campaign_id,
            workflow_id=email_send.workflow_id,
            workflow_step_id=email_send.workflow_step_id,
            email_send_id=email_send.id,
            data={"provider_message_id": message_id},
        )
        await event.insert()

        campaign_name = None
        if email_send.campaign_id:
            campaign = await Campaign.find_one(Campaign.id == email_send.campaign_id)
            if campaign:
                campaign_name = campaign.name

        # Broadcast sent event
        await _broadcast_event_to_websocket(
            event_type="sent",
            user_id=str(email_send.user_id),
            user_email=email_send.to_email,
            campaign_id=str(email_send.campaign_id) if email_send.campaign_id else None,
            campaign_name=campaign_name
        )
    
        logger.info(f"[{email_send_id}] Task completed and committed.")
        
        from .tasks_lead_status import update_user_lead_status_on_event
        update_user_lead_status_on_event.apply_async(
            args=[str(email_send.user_id), "sent"]
        )
            
    try:
        run_async(_run())
    except Exception as exc:
        logger.exception(f"Task send_email_task failed for email_send_id {email_send_id}: {exc}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
@task_metrics
def advance_workflow_task(
    self, instance_id: str, current_node_id: str | None, delay_seconds: int = 0
) -> None:
    """
    Advance a workflow instance from the given node.
    Supports delays by scheduling the task in the future from Celery.
    """

    async def _run() -> None:
        inst_uuid = UUID(instance_id) if isinstance(instance_id, str) else instance_id
        instance = await WorkflowInstance.find_one(WorkflowInstance.id == inst_uuid)
        
        if not instance:
            return

        # Ensure instance is marked as 'running' when it enters the engine
        if instance.status != "running":
            instance.status = "running"
            instance.updated_at = datetime.utcnow()
            await instance.save()

        # Resolve current node (None means start of workflow)
        if current_node_id is None:
            node = await WorkflowNode.find_one(
                WorkflowNode.workflow_id == instance.workflow_id,
                WorkflowNode.type == "start"
            )
        else:
            node_uuid = UUID(current_node_id) if isinstance(current_node_id, str) else current_node_id
            node = await WorkflowNode.find_one(WorkflowNode.id == node_uuid)

        if not node:
            logger.info(f"No node found for {current_node_id}, marking instance {instance.id} as completed.")
            instance.status = "completed"
            instance.updated_at = datetime.utcnow()
            await instance.save()
            return

        step = WorkflowStep(
            instance_id=instance.id,
            node_id=node.id,
            status="running",
            started_at=datetime.utcnow()
        )
        await step.insert()

        user = await User.find_one(User.id == instance.user_id)
        
        campaign_id_str = None
        from .models import Workflow
        wf = await Workflow.find_one(Workflow.id == instance.workflow_id)
        if wf and wf.campaign_id:
            campaign_id_str = str(wf.campaign_id)

        # Broadcast node entry for live canvas animation
        await _broadcast_event_to_websocket(
            event_type="WORKFLOW_NODE_ENTER",
            user_id=str(instance.user_id),
            user_email=user.email if user else "",  
            campaign_id=campaign_id_str,
            workflow_id=str(instance.workflow_id),
            node_id=str(node.id)
        )

        # Define a helper to find the next node
        async def _get_next_node_id(current_node_id: UUID) -> UUID | None:
            edge = await WorkflowEdge.find_one(WorkflowEdge.from_node_id == current_node_id)
            return edge.to_node_id if edge else None

        node_cfg: Dict[str, Any] = node.config or {}
        actual_cfg = node_cfg.get("data", node_cfg) if isinstance(node_cfg, dict) else {}

        if node.type == "start":
            step.status = "completed"
            step.finished_at = datetime.utcnow()
            await step.save()
            
            next_id = await _get_next_node_id(node.id)
            if next_id:
                advance_workflow_task.apply_async(args=[str(instance.id), str(next_id)])
            return

        # Delay node
        if node.type == "delay":
            seconds = int(actual_cfg.get("seconds", actual_cfg.get("hours", 0) * 3600 or 60))
            eta = datetime.utcnow() + timedelta(seconds=seconds)
            
            step.status = "completed"
            step.finished_at = datetime.utcnow()
            await step.save()
            
            next_id = await _get_next_node_id(node.id)
            if next_id:
                advance_workflow_task.apply_async(
                    args=[str(instance.id), str(next_id)], eta=eta
                )
            return

        # Email node
        if node.type == "email":
            template_id = actual_cfg.get("template_id")
            
            if template_id:
                resolved_template_id = None
                try:
                    resolved_template_id = UUID(str(template_id))
                except (ValueError, TypeError):
                    tmpl = await EmailTemplate.find_one(EmailTemplate.name == str(template_id))
                    if tmpl:
                        resolved_template_id = tmpl.id
                
                if resolved_template_id:
                    email_send = EmailSend(
                        template_id=resolved_template_id,
                        user_id=instance.user_id,
                        campaign_id=wf.campaign_id if wf else None,
                        workflow_id=instance.workflow_id,
                        workflow_step_id=step.id,
                        to_email=user.email if user else "",
                        status="queued",
                    )
                    await email_send.insert()
                    
                    # Set metadata on step
                    step.status = "completed"
                    step.finished_at = datetime.utcnow()
                    await step.save()

                    send_email_task.apply_async(args=[str(email_send.id)])
                    
                    # Also schedule next step
                    next_id = await _get_next_node_id(node.id)
                    if next_id:
                        advance_workflow_task.apply_async(args=[str(instance.id), str(next_id)])
                    return
                else:
                    logger.warning(f"Email node {node.id} template '{template_id}' not found. Skipping send.")
            else:
                logger.warning(f"Email node {node.id} missing template_id. Skipping send.")

            step.status = "completed"
            step.finished_at = datetime.utcnow()
            await step.save()

        # End node
        if node.type == "end":
            step.status = "completed"
            step.finished_at = datetime.utcnow()
            await step.save()
            instance.status = "completed"
            instance.updated_at = datetime.utcnow()
            await instance.save()
            logger.info(f"Reached END node for instance {instance.id}")
            return

        # Condition node
        if node.type == "condition":
            step.status = "pending"
            await step.save()
            evaluate_condition_task.apply_async(
                args=[str(instance.id), str(node.id), str(step.id)]
            )
            return

        # Action node
        if node.type == "action":
            action_cfg: Dict[str, Any] = node.config or {}
            action_type = action_cfg.get("action")
            
            if action_type == "update_lead_status":
                status_val = action_cfg.get("status")
                if status_val and user:
                    # Modify Lead status
                    contact = await Contact.find_one(Contact.email == user.email)
                    if contact:
                        lead = await Lead.find_one(Lead.contact_id == contact.id)
                        if lead:
                            try:
                                lead.lead_status = LeadStatusEnum(status_val.lower())
                                await lead.save()
                            except:
                                pass
            
            if action_type == "send_notification":
                msg = action_cfg.get("message", "Lead needs attention")
                notif_event = Event(
                    type="internal_notification",
                    user_id=instance.user_id,
                    workflow_id=instance.workflow_id,
                    data={
                        "message": msg,
                        "user_email": user.email if user else "",
                        "workflow_name": wf.name if wf else "",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                await notif_event.insert()
            
            # Action node completes immediately
            step.status = "completed"
            step.finished_at = datetime.utcnow()
            await step.save()

        # Default completion logic for other types (or after action)
        step.status = "completed"
        step.finished_at = datetime.utcnow()
        await step.save()
        
        # Check if there's a next node. If not, this is also a terminal state.
        next_id = await _get_next_node_id(node.id)
        if not next_id:
            instance.status = "completed"
            instance.updated_at = datetime.utcnow()
            await instance.save()
            logger.info(f"Terminal node reached (no outgoing edges) for instance {instance.id}")
        
        if next_id:
            advance_workflow_task.apply_async(args=[str(instance.id), str(next_id)])

    try:
        run_async(_run())
    except Exception as exc:
        logger.exception(f"Task advance_workflow_task failed for instance {instance_id}: {exc}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
@task_metrics
def evaluate_condition_task(
    self, instance_id: str, node_id: str, step_id: str
) -> None:
    """
    Celery task that evaluates a JSON condition stored on a `condition` node.
    """

    async def _run() -> None:
        instance = await WorkflowInstance.find_one(WorkflowInstance.id == UUID(instance_id))
        if not instance:
            return

        node = await WorkflowNode.find_one(WorkflowNode.id == UUID(node_id))
        if not node:
            return

        step = await WorkflowStep.find_one(WorkflowStep.id == UUID(step_id))
        if not step:
            return

        node_cfg: Dict[str, Any] = node.config or {}
        actual_cfg = node_cfg.get("data", node_cfg) if isinstance(node_cfg, dict) else {}
        condition_json: Dict[str, Any] = actual_cfg.get("condition") or actual_cfg

        # Mark step as running
        step.status = "running"
        step.started_at = step.started_at or datetime.utcnow()
        await step.save()

        # Evaluate declarative condition.
        eval_result = await evaluate_condition(
            user_id=str(instance.user_id),
            condition=condition_json,
            ctx={
                "workflow_id": str(instance.workflow_id),
                "node_id": str(node.id),
                "instance_id": str(instance.id),
            },
        )

        data_obj = await WorkflowInstanceData.find_one(WorkflowInstanceData.instance_id == instance.id)
        current_data = data_obj.data if data_obj else {}

        snapshot = WorkflowSnapshot(
            instance_id=instance.id,
            step_id=step.id,
            node_id=node.id,
            data_snapshot=current_data,
            condition_result={
                "passed": eval_result.passed,
                "details": eval_result.details
            }
        )
        await snapshot.insert()

        from .models import Workflow
        wf = await Workflow.find_one(Workflow.id == instance.workflow_id)

        event = Event(
            type="condition_evaluated",
            user_id=instance.user_id,
            campaign_id=wf.campaign_id if wf else None,
            workflow_id=instance.workflow_id,
            workflow_step_id=step.id,
            data={
                "condition": condition_json,
                "result": eval_result.passed,
                "details": eval_result.details,
                "instance_id": str(instance.id),
                "node_id": str(node.id)
            },
        )
        await event.insert()

        # Decide next edge based on boolean result.
        edges = await WorkflowEdge.find(WorkflowEdge.from_node_id == node.id).to_list()
        
        next_node_id: str | None = None
        fallback_node_id: str | None = None

        for edge in edges:
            cond = edge.condition or {}
            branch = cond.get("branch")
            
            target_bool = None
            if isinstance(branch, bool):
                target_bool = branch
            elif isinstance(branch, str):
                if branch.lower() == "true":
                    target_bool = True
                elif branch.lower() == "false":
                    target_bool = False
            
            if target_bool is None:
                fallback_node_id = str(edge.to_node_id)
                continue

            if target_bool is True and eval_result.passed:
                next_node_id = str(edge.to_node_id)
                break
            if target_bool is False and not eval_result.passed:
                next_node_id = str(edge.to_node_id)
                break
        
        if not next_node_id and fallback_node_id:
            logger.info(f"Using fallback for node {node.id}")
            next_node_id = fallback_node_id

        # Complete step
        step.status = "completed"
        step.finished_at = datetime.utcnow()
        await step.save()

        if next_node_id:
            advance_workflow_task.apply_async(
                args=[str(instance.id), next_node_id]
            )
        else:
            logger.warning(f"Workflow stalled at CONDITION node {node.id}")

    try:
        run_async(_run())
    except Exception as exc:
        logger.exception(f"Task evaluate_condition_task failed for instance {instance_id}: {exc}")
        raise


@celery_app.task(
    name="check_and_retry_unopened_emails",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def check_and_retry_unopened_emails(self) -> None:
    """
    Celery Beat task that runs periodically to check for
    emails that haven't been opened and schedule retries.
    """
    async def _run() -> None:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        now = datetime.utcnow()

        # Find sent emails in last 7 days from campaigns
        sends = await EmailSend.find(
            EmailSend.status == "sent",
            EmailSend.created_at >= seven_days_ago
        ).to_list()

        # Get campaigns to check retry configs
        campaign_ids = list({s.campaign_id for s in sends if s.campaign_id})
        campaigns = await Campaign.find(In(Campaign.id, campaign_ids)).to_list()
        campaign_map = {c.id: c.retry_config for c in campaigns if c.retry_config.get("enabled")}

        for email_send in sends:
            if email_send.campaign_id not in campaign_map:
                continue
                
            # Check if this specific email was opened
            opened = await Event.find_one(
                Event.email_send_id == email_send.id,
                Event.type == "opened"
            )
            
            if opened:
                continue

            retry_config = campaign_map[email_send.campaign_id]
            
            attempts = await EmailRetryAttempt.find(
                EmailRetryAttempt.event_id == email_send.id
            ).sort("-attempt_number").to_list()
            
            first_retry_hours = retry_config.get("first_retry_hours", 48)
            second_retry_hours = retry_config.get("second_retry_hours", 72)
            max_attempts = retry_config.get("max_attempts", 3)
            
            hours_since_send = (now - email_send.created_at).total_seconds() / 3600
            
            sent_event = await Event.find_one(
                Event.email_send_id == email_send.id,
                Event.type == "sent"
            )
            if not sent_event:
                continue

            should_retry = False
            attempt_num = 0

            if len(attempts) == 0 and hours_since_send >= first_retry_hours:
                should_retry = True
                attempt_num = 1
            elif len(attempts) == 1 and hours_since_send >= (first_retry_hours + second_retry_hours):
                should_retry = True
                attempt_num = 2
            elif len(attempts) >= max_attempts - 1:
                mark_as_cold_lead.apply_async(args=[str(email_send.user_id)])
                continue

            if should_retry:
                retry = EmailRetryAttempt(
                    event_id=sent_event.id,
                    attempt_number=attempt_num,
                    scheduled_for=now,
                    status="sent"
                )
                await retry.insert()
                send_email_task.apply_async(args=[str(email_send.id)])
    
    run_async(_run())


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def mark_as_cold_lead(self, user_id: str) -> None:
    """
    Mark a user as a cold lead after max retry attempts.
    """
    async def _run() -> None:
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        user = await User.find_one(User.id == user_uuid)
        if user:
            contact = await Contact.find_one(Contact.email == user.email)
            if contact:
                lead = await Lead.find_one(Lead.contact_id == contact.id)
                if lead:
                    lead.lead_status = LeadStatusEnum.cold
                    lead.updated_at = datetime.utcnow()
                    await lead.save()
                    
                    event = Event(
                        type="lead_marked_cold",
                        user_id=user_uuid,
                        data={"reason": "max_retry_attempts_reached"}
                    )
                    await event.insert()
                    logger.info(f"User {user_id} marked as cold lead.")
    
    run_async(_run())


@celery_app.task(bind=True)
def import_contacts_task(self, contact_list_id: str, file_id: str, mapping: Dict[str, str], skip_invalid: bool, skip_duplicates: bool, owner_id: str) -> Dict[str, Any]:
    """Background task to import contacts with flexible mapping."""
    async def _run() -> Dict[str, Any]:
        from .config import settings
        from redis.asyncio import Redis as AsyncRedis
        import csv
        import io
        from .api.contacts import validate_email_format
        
        logger.info(f"Starting optimized import_contacts_task for list: {contact_list_id}")
        
        try:
            redis = AsyncRedis.from_url(settings.REDIS_URL, decode_responses=True)
            csv_str = await redis.get(file_id)
            if not csv_str:
                raise Exception("Temporary import file expired or not found")
            
            csv_data = io.StringIO(csv_str)
            reader = csv.DictReader(csv_data)
            rows = list(reader)
            total = len(rows)
            
            if total == 0:
                return {"total": 0, "imported": 0, "skipped": 0, "duplicates": 0}

            cl_uuid = UUID(contact_list_id) if isinstance(contact_list_id, str) else contact_list_id
            imported = 0
            skipped = 0
            duplicates = 0
            
            existing_contacts = await Contact.find(Contact.contact_list_id == cl_uuid).to_list()
            existing_emails = {c.email for c in existing_contacts}

            batch_size = 500
            contacts_to_insert = []
            
            for i, row in enumerate(rows):
                email_col = mapping.get("Email")
                first_name_col = mapping.get("First Name")
                last_name_col = mapping.get("Last Name")
                
                email = row.get(email_col, "").strip().lower() if email_col else ""
                if not email:
                    skipped += 1
                    continue
                    
                is_valid, _ = validate_email_format(email)
                if not is_valid and skip_invalid:
                    skipped += 1
                    continue
                        
                if email in existing_emails:
                    if skip_duplicates:
                        duplicates += 1
                        continue
                
                existing_emails.add(email) 
                
                new_contact = Contact(
                    contact_list_id=cl_uuid,
                    email=email,
                    first_name=row.get(first_name_col) if first_name_col else None,
                    last_name=row.get(last_name_col) if last_name_col else None,
                    attributes=row,
                )
                contacts_to_insert.append(new_contact)

                if len(contacts_to_insert) >= batch_size:
                    for c in contacts_to_insert:
                        # Insert ignores duplicates on email in the model level if we use beanie insert safely
                        existing = await Contact.find_one(Contact.contact_list_id == cl_uuid, Contact.email == c.email)
                        if not existing:
                            await c.insert()
                    imported += len(contacts_to_insert)
                    contacts_to_insert = []
                    self.update_state(state='PROGRESS', meta={'progress': int(((i + 1) / total) * 100)})

            if contacts_to_insert:
                for c in contacts_to_insert:
                    existing = await Contact.find_one(Contact.contact_list_id == cl_uuid, Contact.email == c.email)
                    if not existing:
                        await c.insert()
                imported += len(contacts_to_insert)

            # Post-import: Ensure Lead records exist
            all_list_contacts = await Contact.find(Contact.contact_list_id == cl_uuid).to_list()
            contact_ids = [c.id for c in all_list_contacts]
            
            existing_leads = await Lead.find(In(Lead.contact_id, contact_ids)).to_list()
            existing_lead_cids = {l.contact_id for l in existing_leads}
            
            new_leads = []
            for cid in contact_ids:
                if cid not in existing_lead_cids:
                    new_leads.append(Lead(contact_id=cid, lead_status=LeadStatusEnum.new))
                    
            if new_leads:
                for l in new_leads:
                    # check conflict just in case
                    l_exists = await Lead.find_one(Lead.contact_id == l.contact_id)
                    if not l_exists:
                        await l.insert()

            await redis.delete(file_id)
            return {"total": total, "imported": imported, "skipped": skipped, "duplicates": duplicates}
        except Exception as e:
            logger.exception(f"Error in import_contacts_task: {e}")
            raise

    return run_async(_run())


@celery_app.task(name="process_daily_warmup_increase_task")
def process_daily_warmup_increase_task():
    """Daily task to increase warmup volume for all active campaigns."""
    async def _run():
        from .services.reputation import ReputationWarmupService
        service = ReputationWarmupService()
        count = await service.process_daily_increase()
        logger.info(f"Increased warmup limit for {count} campaigns.")

    try:
        run_async(_run())
    except Exception as e:
        logger.exception(f"Error in process_daily_warmup_increase_task: {e}")
        raise


@celery_app.task(name="cleanup_stale_workflow_instances_task")
def cleanup_stale_workflow_instances_task():
    """Identifies and recovers 'stuck' workflow instances (running for > 24h)."""
    async def _run():
        stale_threshold = datetime.utcnow() - timedelta(hours=24)
        
        # Find running instances that haven't been updated
        stale_instances = await WorkflowInstance.find(
            WorkflowInstance.status == "running",
            WorkflowInstance.updated_at <= stale_threshold
        ).to_list()
        
        for instance in stale_instances:
            # Find the last active step
            last_step = await WorkflowStep.find(
                WorkflowStep.instance_id == instance.id
            ).sort("-started_at").limit(1).first_or_none()
            
            if last_step and last_step.status == "running":
                logger.warning(f"Recovering stuck instance {instance.id} at node {last_step.node_id}")
                
                event = Event(
                    type="workflow_instance_recovered",
                    user_id=instance.user_id,
                    workflow_id=instance.workflow_id,
                    data={"reason": "stale_instance_detected", "node_id": str(last_step.node_id)}
                )
                await event.insert()
                
                # Re-trigger advancement from the last known node
                advance_workflow_task.apply_async(
                    args=[str(instance.id), str(last_step.node_id)]
                )
            else:
                # If no running step but instance is 'running', mark as failed
                logger.error(f"Marking orphaned instance {instance.id} as failed")
                instance.status = "failed"
                instance.updated_at = datetime.utcnow()
                await instance.save()
                
                event = Event(
                    type="workflow_instance_failed",
                    user_id=instance.user_id,
                    workflow_id=instance.workflow_id,
                    data={"reason": "stale_instance_no_active_step"}
                )
                await event.insert()

    try:
        run_async(_run())
    except Exception as e:
        logger.exception(f"Error in cleanup_stale_workflow_instances_task: {e}")
        raise
@celery_app.task(name="check_lead_inactivity", bind=True)
def check_lead_inactivity(self) -> None:
    """
    Check for leads with no activity for a defined threshold (default 3 days).
    Notifies the assigned Sales Lead/Team Member.
    """
    async def _run() -> None:
        from .services.notifications import NotificationService
        from .models import Setting
        
        # Get threshold from settings or default to 3 days
        threshold_days = 3
        setting = await Setting.find_one(Setting.key == "crm_inactivity_threshold")
        if setting:
            threshold_days = setting.value.get("days", 3)
            
        cutoff = datetime.utcnow() - timedelta(days=threshold_days)
        
        # We only care about active leads (not won/lost)
        leads = await Lead.find(
            Lead.stage != "won",
            Lead.stage != "lost",
            Lead.last_activity_at < cutoff,
            Lead.assigned_to_id != None
        ).to_list()
        
        for lead in leads:
            # Check if we already notified about this lead recently to avoid spam
            # For now, just notify
            await NotificationService.create_notification(
                user_id=lead.assigned_to_id,
                title="Lead Inactivity Alert",
                message=f"No activity recorded for {lead.company_name} for over {threshold_days} days.",
                type="warning",
                link=f"/leads/{str(lead.id)}"
            )
            logger.info(f"Notified user {lead.assigned_to_id} about inactive lead {lead.id}")

    run_async(_run())
@celery_app.task(name="sync-email-replies")
def sync_email_replies_task():
    """
    Background task to sync email replies from the mailbox 
    and link them to CRM leads.
    """
    async def _run():
        # In a real scenario, we'd fetch IMAP settings from the database
        # For this implementation, we'll look for 'Event' objects of type 'REPLY'
        # or simulate checking a mailbox if configuration exists.
        
        # 1. Get leads that have an associated contact email
        # 2. Check for new interactions (simulated here)
        
        logger.info("Starting email reply sync...")
        # Placeholder for actual IMAP logic
        # For now, let's assume we fetch events from an external tracking pixel or reply-to address
        pass

    run_async(_run())

@celery_app.task(name="sync_dashboard_metrics")
def sync_dashboard_metrics():
    """Scheduled task to pre-calculate dashboard metrics."""
    from .services.analytics import AnalyticsService
    from .models import GlobalMetrics
    from .core.async_runner import run_async
    
    async def _sync():
        logger.info("Syncing dashboard metrics...")
        data = await AnalyticsService.get_dashboard_data(use_cache=False)
        
        # update_one with upsert
        await GlobalMetrics.find_one(
            GlobalMetrics.type == "dashboard", 
            GlobalMetrics.user_id == None
        ).upsert(
            {"$set": {"data": data, "updated_at": datetime.utcnow()}},
            on_insert=GlobalMetrics(type="dashboard", data=data)
        )
        logger.info("Dashboard metrics synced successfully.")
        
    run_async(_sync())
