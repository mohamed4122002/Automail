"""
Declarative workflow condition engine using Beanie ODM.

Conditions are stored as JSON on workflow nodes or edges and interpreted at runtime.
Supported condition types (extensible via the registry below):
  - event_check
  - event_count
  - no_event
  - lead_score_threshold
  - last_activity_days
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict
from uuid import UUID

from .models import Event, LeadScore, EmailSend, EmailRetryAttempt


ConditionContext = Dict[str, Any]


@dataclass
class ConditionResult:
    """Structured result of a condition evaluation."""
    passed: bool
    details: Dict[str, Any]


async def _event_check(
    user_id: str, condition: Dict[str, Any], ctx: ConditionContext
) -> ConditionResult:
    """
    Check if a specific event type occurred within N hours.

    JSON shape:
    {
      "type": "event_check",
      "event": "opened",
      "within_hours": 48
    }
    """
    event_type = condition.get("event")
    within_hours = int(condition.get("within_hours", 0))
    if not event_type or within_hours <= 0:
        return ConditionResult(
            passed=False,
            details={
                "reason": "invalid_condition",
                "message": "event or within_hours missing/invalid",
            },
        )

    since = datetime.utcnow() - timedelta(hours=within_hours)
    
    count = await Event.find(
        Event.user_id == UUID(user_id),
        Event.type == event_type,
        Event.created_at >= since
    ).count()
    
    return ConditionResult(
        passed=count > 0,
        details={
            "event": event_type,
            "within_hours": within_hours,
            "count": count,
        },
    )


async def _event_count(
    user_id: str, condition: Dict[str, Any], ctx: ConditionContext
) -> ConditionResult:
    """
    Check if count of events satisfies a comparison.

    JSON shape:
    {
      "type": "event_count",
      "event": "clicked",
      "op": ">=",
      "count": 2,
      "within_hours": 72   # optional
    }
    """
    event_type = condition.get("event")
    op = str(condition.get("op", "=="))
    target = int(condition.get("count", 0))
    within_hours = condition.get("within_hours")

    if not event_type:
        return ConditionResult(
            passed=False,
            details={"reason": "invalid_condition", "message": "event missing"},
        )

    filters = [Event.user_id == UUID(user_id), Event.type == event_type]
    if within_hours is not None:
        since = datetime.utcnow() - timedelta(hours=int(within_hours))
        filters.append(Event.created_at >= since)

    count = await Event.find(*filters).count()

    ops: Dict[str, Callable[[int, int], bool]] = {
        "==": lambda a, b: a == b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
    }
    cmp = ops.get(op)
    passed = cmp(count, target) if cmp else False

    return ConditionResult(
        passed=passed,
        details={
            "event": event_type,
            "op": op,
            "target": target,
            "actual": count,
            "within_hours": within_hours,
        },
    )


async def _no_event(
    user_id: str, condition: Dict[str, Any], ctx: ConditionContext
) -> ConditionResult:
    """
    Pass if NO events of a given type exist in a time window.
    """
    event_type = condition.get("event")
    within_hours = int(condition.get("within_hours", 0))
    if not event_type or within_hours <= 0:
        return ConditionResult(
            passed=False,
            details={
                "reason": "invalid_condition",
                "message": "event or within_hours missing/invalid",
            },
        )

    since = datetime.utcnow() - timedelta(hours=within_hours)
    
    count = await Event.find(
        Event.user_id == UUID(user_id),
        Event.type == event_type,
        Event.created_at >= since
    ).count()
    
    return ConditionResult(
        passed=count == 0,
        details={
            "event": event_type,
            "within_hours": within_hours,
            "count": count,
        },
    )


async def _lead_score_threshold(
    user_id: str, condition: Dict[str, Any], ctx: ConditionContext
) -> ConditionResult:
    """
    Compare lead score to a threshold.
    """
    op = str(condition.get("op", ">="))
    target = int(condition.get("score", 0))

    lead_score_doc = await LeadScore.find_one(LeadScore.user_id == UUID(user_id))
    score = lead_score_doc.score if lead_score_doc else 0

    ops: Dict[str, Callable[[int, int], bool]] = {
        "==": lambda a, b: a == b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
    }
    cmp = ops.get(op)
    passed = cmp(score, target) if cmp else False

    return ConditionResult(
        passed=passed,
        details={"op": op, "target": target, "score": score},
    )


async def _last_activity_days(
    user_id: str, condition: Dict[str, Any], ctx: ConditionContext
) -> ConditionResult:
    """
    Check if last activity is within/outside a number of days.
    """
    op = str(condition.get("op", "<="))
    days = int(condition.get("days", 0))

    last_event = await Event.find(Event.user_id == UUID(user_id)).sort("-created_at").limit(1).first_or_none()
    
    if last_event is None:
        # No activity at all; treat as very old
        return ConditionResult(
            passed=op in {">", ">="},
            details={"last_activity": None, "days": days},
        )

    delta_days = (datetime.utcnow() - last_event.created_at).days
    ops: Dict[str, Callable[[int, int], bool]] = {
        "==": lambda a, b: a == b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
    }
    cmp = ops.get(op)
    passed = cmp(delta_days, days) if cmp else False

    return ConditionResult(
        passed=passed,
        details={"op": op, "days": days, "actual_days": delta_days},
    )


async def _email_not_opened_after_hours(
    user_id: str, condition: Dict[str, Any], ctx: ConditionContext
) -> ConditionResult:
    """
    Check if an email was sent but NOT opened within N hours.
    This is the core condition for the Non-Responder retry logic.
    """
    hours = int(condition.get("hours", 48))
    email_send_id = condition.get("email_send_id")
    
    filters = [EmailSend.user_id == UUID(user_id), EmailSend.status == "sent"]
    if email_send_id:
        filters.append(EmailSend.id == UUID(email_send_id))
    
    # Get the most recent sent email
    email_send = await EmailSend.find(*filters).sort("-created_at").limit(1).first_or_none()
    
    if not email_send:
        return ConditionResult(
            passed=False,
            details={"reason": "no_email_sent", "message": "No email found for this user"}
        )
    
    # Check if enough time has passed
    time_since_send = datetime.utcnow() - email_send.created_at
    if time_since_send.total_seconds() < (hours * 3600):
        return ConditionResult(
            passed=False,
            details={
                "reason": "too_soon",
                "hours_since_send": time_since_send.total_seconds() / 3600,
                "required_hours": hours
            }
        )
    
    opened_count = await Event.find(
        Event.user_id == UUID(user_id),
        Event.email_send_id == email_send.id,
        Event.type == "opened"
    ).count()
    
    passed = opened_count == 0
    
    return ConditionResult(
        passed=passed,
        details={
            "email_send_id": str(email_send.id),
            "hours_since_send": time_since_send.total_seconds() / 3600,
            "was_opened": opened_count > 0,
            "open_count": opened_count
        }
    )


async def _retry_attempt_count(
    user_id: str, condition: Dict[str, Any], ctx: ConditionContext
) -> ConditionResult:
    """
    Check how many retry attempts have been made for a user/campaign.
    """
    op = str(condition.get("op", "<"))
    target = int(condition.get("count", 3))
    campaign_id = condition.get("campaign_id")
    
    filters = [EmailRetryAttempt.user_id == UUID(user_id), EmailRetryAttempt.status == "sent"]
    if campaign_id:
        filters.append(EmailRetryAttempt.campaign_id == UUID(campaign_id))
    
    count = await EmailRetryAttempt.find(*filters).count()
    
    ops: Dict[str, Callable[[int, int], bool]] = {
        "==": lambda a, b: a == b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
    }
    cmp = ops.get(op)
    passed = cmp(count, target) if cmp else False
    
    return ConditionResult(
        passed=passed,
        details={
            "op": op,
            "target": target,
            "actual_count": count
        }
    )


async def _opened_no_click(
    user_id: str, condition: Dict[str, Any], ctx: ConditionContext
) -> ConditionResult:
    """
    Check if a user has opened an email but NOT clicked any links.
    Useful for Path 2 transitions.
    """
    within_hours = int(condition.get("within_hours", 48))
    since = datetime.utcnow() - timedelta(hours=within_hours)
    
    open_count = await Event.find(
        Event.user_id == UUID(user_id),
        Event.type == "opened",
        Event.created_at >= since
    ).count()
    
    click_count = await Event.find(
        Event.user_id == UUID(user_id),
        Event.type == "clicked",
        Event.created_at >= since
    ).count()
    
    passed = open_count > 0 and click_count == 0
    
    return ConditionResult(
        passed=passed,
        details={
            "open_count": open_count,
            "click_count": click_count,
            "within_hours": within_hours
        }
    )


CONDITION_HANDLERS: Dict[
    str, Callable[[str, Dict[str, Any], ConditionContext], Any]
] = {
    "event_check": _event_check,
    "event_count": _event_count,
    "no_event": _no_event,
    "lead_score_threshold": _lead_score_threshold,
    "last_activity_days": _last_activity_days,
    "email_not_opened_after_hours": _email_not_opened_after_hours,
    "retry_attempt_count": _retry_attempt_count,
    "opened_no_click": _opened_no_click,
}


async def evaluate_condition(
    user_id: str,
    condition: Dict[str, Any],
    ctx: ConditionContext | None = None,
) -> ConditionResult:
    import logging
    logger = logging.getLogger(__name__)

    ctx = ctx or {}
    cond_type = condition.get("type")
    handler = CONDITION_HANDLERS.get(cond_type)
    
    if handler is None:
        logger.warning(f"Unknown condition type: {cond_type}")
        return ConditionResult(
            passed=False,
            details={
                "reason": "unknown_condition_type",
                "condition_type": cond_type,
            },
        )
    
    # Execute handler
    result = await handler(user_id, condition, ctx)
    
    logger.info(
        f"Condition Evaluation: type={cond_type}, user={user_id}, "
        f"passed={result.passed}, details={result.details}"
    )
    
    return result
