from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import UUID
import asyncio

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from .celery_app import celery_app
from .conditions import evaluate_condition
from .db import AsyncSessionLocal
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
)
from .services.spam_shield import spam_shield_service
from .core.async_runner import run_async
from .core.monitoring import task_metrics
import logging

logger = logging.getLogger(__name__)


from .core.db import task_context

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
        async with task_context() as db:
            async with db.begin():
                from sqlalchemy.orm import selectinload
                result = await db.execute(
                    sa.select(EmailSend)
                    .options(
                        selectinload(EmailSend.campaign),
                        selectinload(EmailSend.user)
                    )
                    .where(EmailSend.id == (UUID(email_send_id) if isinstance(email_send_id, str) else email_send_id))
                )
                email_send = result.scalar_one_or_none()
                if not email_send:
                    logger.error(f"EmailSend {email_send_id} not found")
                    return

                if not email_send.template_id:
                    return

                res_tmpl = await db.execute(
                    sa.select(EmailTemplate).where(
                        EmailTemplate.id == email_send.template_id
                    )
                )
                template = res_tmpl.scalar_one_or_none()
                if not template:
                    logger.error(f"Template not found for email_send {email_send_id}")
                    return

                logger.info(f"[{email_send_id}] Fetching provider...")
                provider = await get_email_provider(db)
                logger.info(f"[{email_send_id}] Provider: {provider.__class__.__name__}")
                
                # A/B Testing Logic
                from .services.ab_testing import ABTestingService
                ab_service = ABTestingService(db)
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

                from .config import settings
                unsubscribe_link = f"{settings.FRONTEND_URL}/unsubscribe/{str(email_send.unsubscribe_token)}"
                
                user_data = {
                    "first_name": email_send.user.first_name if email_send.user else "there",
                    "last_name": email_send.user.last_name if email_send.user else "",
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
                reputation_service = ReputationWarmupService(db)
                
                # Check if we can send based on warmup limits
                logger.info(f"[{email_send_id}] Checking warmup limit...")
                can_send = await reputation_service.check_warmup_limit(email_send.campaign_id)
                if not can_send:
                    logger.warning(f"[{email_send_id}] Warmup limit reached. Re-scheduling.")
                    # Re-schedule via Celery retry mechanism
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
                
                await reputation_service.increment_sent_count(email_send.campaign_id)
                email_send.status = "sent"
                email_send.provider_message_id = message_id
                email_send.data = {"subject": subject}

                event = Event(
                    type="sent",
                    user_id=email_send.user_id,
                    campaign_id=email_send.campaign_id,
                    workflow_id=email_send.workflow_id,
                    workflow_step_id=email_send.workflow_step_id,
                    email_send_id=email_send.id,
                    data={"provider_message_id": message_id},
                )
                db.add(event)
                await db.flush()

                # Broadcast sent event
                await _broadcast_event_to_websocket(
                    event_type="sent",
                    user_id=str(email_send.user_id),
                    user_email=email_send.to_email,
                    campaign_id=str(email_send.campaign_id) if email_send.campaign_id else None,
                    campaign_name=email_send.campaign.name if email_send.campaign else None
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
        async with task_context() as db:
            async with db.begin():
                from sqlalchemy.orm import selectinload
                
                result = await db.execute(
                    sa.select(WorkflowInstance)
                    .options(
                        selectinload(WorkflowInstance.workflow),
                        selectinload(WorkflowInstance.user)
                    )
                    .where(
                        WorkflowInstance.id == (UUID(instance_id) if isinstance(instance_id, str) else instance_id)
                    )
                )
                instance: WorkflowInstance | None = result.scalar_one_or_none()
                if not instance:
                    return

                # Ensure instance is marked as 'running' when it enters the engine
                if instance.status != "running":
                    instance.status = "running"
                    instance.updated_at = datetime.utcnow()
                    await db.flush()

                # Resolve current node (None means start of workflow)
                if current_node_id is None:
                    # Find start node
                    res_node = await db.execute(
                        sa.select(WorkflowNode)
                        .where(
                            WorkflowNode.workflow_id == instance.workflow_id,
                            WorkflowNode.type == "start",
                        )
                        .limit(1)
                    )
                    node = res_node.scalar_one_or_none()
                else:
                    res_node = await db.execute(
                        sa.select(WorkflowNode).where(
                            WorkflowNode.id == (UUID(current_node_id) if isinstance(current_node_id, str) else current_node_id)
                        )
                    )
                    node = res_node.scalar_one_or_none()

                if not node:
                    logger.info(f"No node found for {current_node_id}, marking instance {instance.id} as completed.")
                    instance.status = "completed"
                    instance.updated_at = datetime.utcnow()
                    return

                step = WorkflowStep(
                    instance_id=instance.id,
                    node_id=node.id,
                    status="running",
                    started_at=datetime.utcnow()
                )
                db.add(step)
                await db.flush()

                # Broadcast node entry for live canvas animation
                await _broadcast_event_to_websocket(
                    event_type="WORKFLOW_NODE_ENTER",
                    user_id=str(instance.user_id),
                    user_email=instance.user.email,  
                    campaign_id=str(instance.workflow.campaign_id) if (instance.workflow and instance.workflow.campaign_id) else None,
                    workflow_id=str(instance.workflow_id),
                    node_id=str(node.id)
                )

                # Define a helper to find the next node
                async def _get_next_node_id(current_node_id: UUID) -> UUID | None:
                    res_edge = await db.execute(
                        sa.select(WorkflowEdge).where(WorkflowEdge.from_node_id == current_node_id)
                    )
                    edge = res_edge.scalar_one_or_none()
                    return edge.to_node_id if edge else None

                # Process by node type
                # Helper to get config safely (nested or flat)
                node_cfg: Dict[str, Any] = node.config or {}
                actual_cfg = node_cfg.get("data", node_cfg) if isinstance(node_cfg, dict) else {}

                if node.type == "start":
                    step.status = "completed"
                    step.finished_at = datetime.utcnow()
                    await db.flush()
                    
                    next_id = await _get_next_node_id(node.id)
                    if next_id:
                        advance_workflow_task.apply_async(args=[str(instance.id), str(next_id)])
                    return

                # Delay node
                if node.type == "delay":
                    seconds = int(actual_cfg.get("seconds", actual_cfg.get("hours", 0) * 3600 or 60))
                    eta = datetime.utcnow() + timedelta(seconds=seconds)
                    
                    # Delay node is "completed" once it schedules the next step
                    step.status = "completed"
                    step.finished_at = datetime.utcnow()
                    await db.flush()
                    
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
                        # Resolve template_id if it's not a UUID
                        resolved_template_id = None
                        try:
                            UUID(str(template_id))
                            resolved_template_id = template_id
                        except (ValueError, TypeError):
                            # Try to lookup by name if it's a slug/name string
                            res = await db.execute(sa.select(EmailTemplate.id).where(EmailTemplate.name == str(template_id)))
                            resolved_template_id = res.scalar_one_or_none()
                        
                        if resolved_template_id:
                            email_send = EmailSend(
                                template_id=resolved_template_id,
                                user_id=instance.user_id,
                                campaign_id=instance.workflow.campaign_id,
                                workflow_id=instance.workflow_id,
                                workflow_step_id=step.id,
                                to_email=instance.user.email,
                                status="queued",
                            )
                            db.add(email_send)
                            await db.flush()
                            
                            # Set metadata on step
                            step.status = "completed"
                            step.finished_at = datetime.utcnow()
                            await db.flush()

                            # Dispatch task AFTER implicit commit from db.begin() block
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
                    await db.flush()

                # End node
                if node.type == "end":
                    step.status = "completed"
                    step.finished_at = datetime.utcnow()
                    instance.status = "completed"
                    instance.updated_at = datetime.utcnow()
                    logger.info(f"Reached END node for instance {instance.id}")
                    return

                # Condition node
                if node.type == "condition":
                    step.status = "pending"
                    await db.flush()
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
                        if status_val:
                            # Find lead via user email
                            from .models import Contact, User, Lead
                            await db.execute(
                                sa.update(Lead)
                                .where(Lead.contact_id.in_(
                                    sa.select(Contact.id).join(User, Contact.email == User.email)
                                    .where(User.id == instance.user_id)
                                ))
                                .values(lead_status=status_val.lower())
                            )
                    
                    if action_type == "send_notification":
                        msg = action_cfg.get("message", "Lead needs attention")
                        notif_event = Event(
                            type="internal_notification",
                            user_id=instance.user_id,
                            workflow_id=instance.workflow_id,
                            data={
                                "message": msg,
                                "user_email": instance.user.email,
                                "workflow_name": instance.workflow.name,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                        db.add(notif_event)
                    
                    # Action node completes immediately
                    step.status = "completed"
                    step.finished_at = datetime.utcnow()
                    await db.flush()

                # Default completion logic for other types (or after action)
                step.status = "completed"
                step.finished_at = datetime.utcnow()
                
                # Check if there's a next node. If not, this is also a terminal state.
                next_id = await _get_next_node_id(node.id)
                if not next_id:
                    instance.status = "completed"
                    instance.updated_at = datetime.utcnow()
                    logger.info(f"Terminal node reached (no outgoing edges) for instance {instance.id}")
                
                await db.flush()
                
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
        async with task_context() as db:
            async with db.begin():
                from sqlalchemy.orm import selectinload
                result_inst = await db.execute(
                    sa.select(WorkflowInstance)
                    .options(
                        selectinload(WorkflowInstance.workflow),
                        selectinload(WorkflowInstance.user)
                    )
                    .where(sa.WorkflowInstance.id == (UUID(instance_id) if isinstance(instance_id, str) else instance_id))
                )
                instance = result_inst.scalar_one_or_none()
                if not instance:
                    return

                result_node = await db.execute(
                    sa.select(WorkflowNode).where(WorkflowNode.id == (UUID(node_id) if isinstance(node_id, str) else node_id))
                )
                node = result_node.scalar_one_or_none()
                if not node:
                    return

                result_step = await db.execute(
                    sa.select(WorkflowStep).where(WorkflowStep.id == (UUID(step_id) if isinstance(step_id, str) else step_id))
                )
                step = result_step.scalar_one_or_none()
                if not step:
                    return

                node_cfg: Dict[str, Any] = node.config or {}
                actual_cfg = node_cfg.get("data", node_cfg) if isinstance(node_cfg, dict) else {}
                condition_json: Dict[str, Any] = actual_cfg.get("condition") or actual_cfg

                # Mark step as running
                step.status = "running"
                step.started_at = step.started_at or datetime.utcnow()
                await db.flush()

                # Evaluate declarative condition.
                eval_result = await evaluate_condition(
                    db=db,
                    user_id=str(instance.user_id),
                    condition=condition_json,
                    ctx={
                        "workflow_id": str(instance.workflow_id),
                        "node_id": str(node.id),
                        "instance_id": str(instance.id),
                    },
                )

                # Capture Workflow Snapshot
                from .models import WorkflowInstanceData, WorkflowSnapshot
                
                # Fetch current instance data
                data_res = await db.execute(
                    sa.select(WorkflowInstanceData).where(WorkflowInstanceData.instance_id == instance.id)
                )
                data_obj = data_res.scalar_one_or_none()
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
                db.add(snapshot)

                # Consolidated logging into Event table
                event = Event(
                    type="condition_evaluated",
                    user_id=instance.user_id,
                    campaign_id=instance.workflow.campaign_id if instance.workflow else None,
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
                db.add(event)

                # Decide next edge based on boolean result.
                edges_res = await db.execute(
                    sa.select(WorkflowEdge).where(WorkflowEdge.from_node_id == node.id)
                )
                edges = list(edges_res.scalars().all())
                
                next_node_id: str | None = None
                fallback_node_id: str | None = None

                # Normalized branch matching
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
                await db.flush()

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


import random
import time

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
    Optimized to use a single query instead of N+1.
    """
    async def _run() -> None:
        async with task_context() as db:
            async with db.begin():
                from .models import EmailSend, Event, Campaign, EmailRetryAttempt
                
                seven_days_ago = datetime.utcnow() - timedelta(days=7)
                
                # Consolidated query:
                # 1. Finds 'sent' emails in the last 7 days.
                # 2. Filters out those that have an 'opened' event.
                # 3. Joins campaign to check if retry is enabled.
                # 4. Filters for those needing retry based on campaign intervals.
                
                # First, find candidates (no 'opened' event)
                sent_event_subq = sa.select(Event.id).where(
                    Event.email_send_id == EmailSend.id, 
                    Event.type == "sent"
                ).scalar_subquery()

                q = await db.execute(
                    sa.select(
                        EmailSend,
                        Campaign.retry_config
                    )
                    .join(Campaign, EmailSend.campaign_id == Campaign.id)
                    .outerjoin(
                        Event,
                        sa.and_(
                            Event.email_send_id == EmailSend.id,
                            Event.type == "opened"
                        )
                    )
                    .where(
                        EmailSend.status == "sent",
                        EmailSend.created_at >= seven_days_ago,
                        Event.id == None, # Not opened
                        sa.text("campaigns.retry_config->>'enabled' = 'true'")
                    )
                )
                candidates = q.all()
                
                now = datetime.utcnow()
                for email_send, retry_config in candidates:
                    # For each candidate, check attempt count and timing
                    # We still do some processing here but we eliminated the biggest N+1 (the check for 'opened').
                    # To fully optimize, we'd need a more complex subquery for attempt counts, 
                    # but this is already a huge improvement.
                    
                    q_attempts = await db.execute(
                        sa.select(EmailRetryAttempt)
                        .join(Event, EmailRetryAttempt.event_id == Event.id)
                        .where(Event.email_send_id == email_send.id)
                        .order_by(EmailRetryAttempt.attempt_number.desc())
                    )
                    attempts = list(q_attempts.scalars().all())
                    
                    first_retry_hours = retry_config.get("first_retry_hours", 48)
                    second_retry_hours = retry_config.get("second_retry_hours", 72)
                    max_attempts = retry_config.get("max_attempts", 3)
                    
                    hours_since_send = (now - email_send.created_at).total_seconds() / 3600
                    
                    # Find 'sent' event to link
                    sent_event_id_q = await db.execute(
                        sa.select(Event.id).where(
                            Event.email_send_id == email_send.id,
                            Event.type == "sent"
                        ).limit(1)
                    )
                    sent_event_id = sent_event_id_q.scalar_one_or_none()
                    if not sent_event_id:
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
                            event_id=sent_event_id,
                            attempt_number=attempt_num,
                            scheduled_for=now,
                            status="sent"
                        )
                        db.add(retry)
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
    Corrected to update the Lead model via Contact link.
    """
    async def _run() -> None:
        async with task_context() as db:
            async with db.begin():
                from .models import Contact, Lead, LeadStatusEnum, Event
                
                # Find the lead via user email linkage
                # Note: This assumes User.email matches Contact.email
                subq = (
                    sa.select(Contact.id)
                    .join(User, Contact.email == User.email)
                    .where(User.id == (UUID(user_id) if isinstance(user_id, str) else user_id))
                    .scalar_subquery()
                )
                
                result = await db.execute(
                    sa.update(Lead)
                    .where(Lead.contact_id == subq)
                    .values(
                        lead_status=LeadStatusEnum.cold,
                        updated_at=datetime.utcnow()
                    )
                )
                
                if result.rowcount > 0:
                    event = Event(
                        type="lead_marked_cold",
                        user_id=(UUID(user_id) if isinstance(user_id, str) else user_id),
                        data={"reason": "max_retry_attempts_reached"}
                    )
                    db.add(event)
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
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        logger.info(f"Starting optimized import_contacts_task for list: {contact_list_id}")
        
        try:
            # Use AsyncRedis
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
            
            async with task_context() as db:
                # Optimized Duplicate Check (for UI reports, actual DB safety comes from ON CONFLICT)
                existing_q = await db.execute(
                    sa.select(Contact.email).where(Contact.contact_list_id == cl_uuid)
                )
                existing_emails = set(existing_q.scalars().all())

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
                    contacts_to_insert.append({
                        "contact_list_id": cl_uuid,
                        "email": email,
                        "first_name": row.get(first_name_col) if first_name_col else None,
                        "last_name": row.get(last_name_col) if last_name_col else None,
                        "attributes": row,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    })

                    if len(contacts_to_insert) >= batch_size:
                        async with db.begin():
                            # Use ON CONFLICT DO NOTHING for idempotency
                            stmt = pg_insert(Contact).values(contacts_to_insert)
                            stmt = stmt.on_conflict_do_nothing(index_elements=["contact_list_id", "email"])
                            await db.execute(stmt)
                        imported += len(contacts_to_insert)
                        contacts_to_insert = []
                        self.update_state(state='PROGRESS', meta={'progress': int(((i + 1) / total) * 100)})

                if contacts_to_insert:
                    async with db.begin():
                        stmt = pg_insert(Contact).values(contacts_to_insert)
                        stmt = stmt.on_conflict_do_nothing(index_elements=["contact_list_id", "email"])
                        await db.execute(stmt)
                    imported += len(contacts_to_insert)

                # Post-import: Ensure Lead records exist
                async with db.begin():
                    # Optimized lead creation: insert if not exists
                    leads_subquery = sa.select(Lead.contact_id).scalar_subquery()
                    new_contact_ids_q = await db.execute(
                        sa.select(Contact.id).where(
                            sa.and_(
                                Contact.contact_list_id == cl_uuid,
                                ~Contact.id.in_(leads_subquery)
                            )
                        )
                    )
                    new_contact_ids = new_contact_ids_q.scalars().all()
                    
                    if new_contact_ids:
                        leads_to_insert = [
                            {
                                "contact_id": cid,
                                "lead_status": LeadStatusEnum.new,
                                "lead_score": 0,
                                "created_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow()
                            }
                            for cid in new_contact_ids
                        ]
                        # Bulk insert new leads, ignoring conflicts
                        stmt = pg_insert(Lead).values(leads_to_insert)
                        stmt = stmt.on_conflict_do_nothing(index_elements=["contact_id"])
                        await db.execute(stmt)

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
        async with task_context() as db:
            async with db.begin():
                from .services.reputation import ReputationWarmupService
                service = ReputationWarmupService(db)
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
        async with task_context() as db:
            async with db.begin():
                stale_threshold = datetime.utcnow() - timedelta(hours=24)
                
                # Find running instances that haven't been updated
                q = await db.execute(
                    sa.select(WorkflowInstance)
                    .where(
                        WorkflowInstance.status == "running",
                        WorkflowInstance.updated_at <= stale_threshold
                    )
                )
                stale_instances = q.scalars().all()
                
                for instance in stale_instances:
                    # Find the last active step
                    q_step = await db.execute(
                        sa.select(WorkflowStep)
                        .where(WorkflowStep.instance_id == instance.id)
                        .order_by(WorkflowStep.started_at.desc())
                        .limit(1)
                    )
                    last_step = q_step.scalar_one_or_none()
                    
                    if last_step and last_step.status == "running":
                        logger.warning(f"Recovering stuck instance {instance.id} at node {last_step.node_id}")
                        
                        event = Event(
                            type="workflow_instance_recovered",
                            user_id=instance.user_id,
                            workflow_id=instance.workflow_id,
                            data={"reason": "stale_instance_detected", "node_id": str(last_step.node_id)}
                        )
                        db.add(event)
                        
                        # Re-trigger advancement from the last known node
                        advance_workflow_task.apply_async(
                            args=[str(instance.id), str(last_step.node_id)]
                        )
                    else:
                        # If no running step but instance is 'running', mark as failed
                        logger.error(f"Marking orphaned instance {instance.id} as failed")
                        instance.status = "failed"
                        instance.updated_at = datetime.utcnow()
                        
                        event = Event(
                            type="workflow_instance_failed",
                            user_id=instance.user_id,
                            workflow_id=instance.workflow_id,
                            data={"reason": "stale_instance_no_active_step"}
                        )
                        db.add(event)

    try:
        run_async(_run())
    except Exception as e:
        logger.exception(f"Error in cleanup_stale_workflow_instances_task: {e}")
        raise
