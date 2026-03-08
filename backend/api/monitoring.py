from beanie.operators import In
"""
Enhanced Monitoring API — DB Hardening
Provides health checks, connection pool stats, security status, and index health.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta

from ..models import Campaign, User, EmailSend, Event, WorkflowInstance, WorkflowStep
from ..auth import get_current_user, get_current_user_roles
from ..config import settings

from redis import Redis
from ..services.campaign_manager import CampaignManagerService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/monitor", tags=["monitoring"])


# ── Health Check (public) ─────────────────────────────────────────────────────

@router.get("/health", summary="Service health check")
async def health_check() -> Dict[str, Any]:
    """
    Check health of all services: MongoDB, Redis, Celery.
    Returns 200 even if degraded (so frontend can show partial outage UI).
    Returns 503 only if ALL services are down.
    """
    health: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
    }

    # 1. MongoDB
    try:
        from ..db import check_db_connection
        is_healthy = await check_db_connection()
        if is_healthy:
            health["services"]["mongodb"] = "healthy"
        else:
            health["services"]["mongodb"] = "unhealthy"
            health["status"] = "degraded"
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")
        health["services"]["mongodb"] = "unhealthy"
        health["status"] = "degraded"

    # 3. Redis
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        r.ping()
        info = r.info("memory")
        health["services"]["redis"] = {
            "status": "healthy",
            "memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # 4. Celery
    try:
        from ..celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=2)
        ping = inspector.ping()
        if ping:
            worker_count = len(ping)
            health["services"]["celery"] = {"status": "healthy", "workers": worker_count}
        else:
            health["services"]["celery"] = {"status": "no_workers"}
            health["status"] = "degraded"
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        health["services"]["celery"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"

    # 503 only if everything is down
    all_down = all(
        (v if isinstance(v, str) else v.get("status", "")) in ("unhealthy", "error", "no_workers")
        for v in health["services"].values()
    )
    if all_down:
        raise HTTPException(status_code=503, detail="All services unavailable")

    return health


# ── Security Status (admin) ───────────────────────────────────────────────────

@router.get("/security-status", summary="Security configuration status")
async def get_security_status(
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Audit security configuration: encryption, CORS, JWT, and sensitive settings.
    Flags any misconfiguration that could be a security risk.
    """
    if "admin" not in current_admin.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    issues: List[str] = []
    checks: Dict[str, Any] = {}

    # 1. Check encryption key is not the old default
    old_dev_key = "YwzejqHbvb-foxv1ZbLMEuvaL2H_ybf9CHanjdzVzXA="
    if settings.SETTINGS_ENCRYPTION_KEY == old_dev_key:
        issues.append("CRITICAL: SETTINGS_ENCRYPTION_KEY is still the old hardcoded dev key!")
        checks["encryption_key"] = "INSECURE — using default dev key"
    else:
        checks["encryption_key"] = "OK — custom key configured"

    # 2. Check JWT secret strength
    if len(settings.JWT_SECRET_KEY) < 32:
        issues.append("JWT_SECRET_KEY is too short (< 32 chars)")
        checks["jwt_secret"] = "WEAK"
    else:
        checks["jwt_secret"] = f"OK — {len(settings.JWT_SECRET_KEY)} chars"

    # 3. Check CORS
    if settings.CORS_ORIGINS == "*":
        issues.append("CORS_ORIGINS is '*' — all origins allowed (OK for dev, NOT for prod)")
        checks["cors"] = "OPEN — wildcard"
    else:
        checks["cors"] = f"OK — {settings.CORS_ORIGINS}"

    # 4. Check ENV
    checks["environment"] = settings.ENV

    # 5. Check sensitive settings are actually encrypted in DB
    try:
        from ..models import Setting
        sensitive_keys = ["email_provider", "smtp_config", "api_keys"]
        for key in sensitive_keys:
            setting = await Setting.find_one(Setting.key == key)
            if setting:
                if not setting.is_encrypted:
                    issues.append(f"Setting '{key}' exists but is NOT marked as encrypted!")
                    checks[f"setting_{key}"] = "UNENCRYPTED"
                elif not isinstance(setting.value, dict) or "encrypted" not in setting.value:
                    issues.append(f"Setting '{key}' is marked encrypted but value is plain text!")
                    checks[f"setting_{key}"] = "MARKED_ENCRYPTED_BUT_PLAIN"
                else:
                    checks[f"setting_{key}"] = "OK — encrypted"
            else:
                checks[f"setting_{key}"] = "not configured"
    except Exception as e:
        checks["settings_check"] = f"error: {e}"

    # 6. Check DB URL doesn't contain password in logs
    db_url_safe = settings.MONGODB_URL.split("@")[-1] if "@" in settings.MONGODB_URL else "hidden"
    checks["db_host"] = db_url_safe

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "ISSUES_FOUND" if issues else "OK",
        "issue_count": len(issues),
        "issues": issues,
        "checks": checks,
    }


# ── System Stats (admin) ──────────────────────────────────────────────────────

@router.get("/system", summary="System-wide metrics")
async def get_system_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get system-wide metrics and health status."""
    roles = await get_current_user_roles(current_user)
    if not any(r in roles for r in ["admin", "sales_lead"]):
        raise HTTPException(status_code=403, detail="Admin or Sales Lead access required")

    campaign_count = await Campaign.find_all().count()
    user_count = await User.find_all().count()
    sent_count = await EmailSend.find(EmailSend.status == "sent").count()
    queued_count = await EmailSend.find(EmailSend.status == "queued").count()

    active_workflows = await WorkflowInstance.find(WorkflowInstance.status == "running").count()

    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_events_count = await Event.find(Event.created_at >= yesterday).count()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "campaigns": campaign_count,
            "users": user_count,
            "emails_sent": sent_count,
            "emails_queued": queued_count,
            "active_workflow_instances": active_workflows,
            "events_24h": recent_events_count,
        }
    }


# ── Workflow Health (admin) ───────────────────────────────────────────────────

@router.get("/workflow/health", summary="Workflow instance health")
async def get_workflow_health(
    current_user: User = Depends(get_current_user)
):
    """Get metrics on workflow instances and stalled detections."""
    roles = await get_current_user_roles(current_user)
    if not any(r in roles for r in ["admin", "sales_lead"]):
        raise HTTPException(status_code=403, detail="Admin or Sales Lead access required")
    service = CampaignManagerService()
    return await service.get_workflow_health()


@router.post("/workflow/repair", summary="Repair stalled workflows")
async def repair_stalled_workflows(
    current_admin: User = Depends(get_current_user)
):
    """Trigger a repair for all stalled workflow instances."""
    if "admin" not in current_admin.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    service = CampaignManagerService()
    return await service.repair_stalled_instances()


# ── Campaign Monitoring (admin) ───────────────────────────────────────────────

@router.get("/campaign/{campaign_id}", summary="Campaign monitoring detail")
async def get_campaign_monitoring(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed monitoring for a specific campaign."""
    roles = await get_current_user_roles(current_user)
    if not any(r in roles for r in ["admin", "sales_lead"]):
        raise HTTPException(status_code=403, detail="Admin or Sales Lead access required")

    campaign = await Campaign.find_one(Campaign.id == campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recent_events = await Event.find(
        Event.campaign_id == campaign_id
    ).sort("-created_at").limit(20).to_list()

    # Manual aggregation in Python for performance (if small) or use Beanie
    instances = await WorkflowInstance.find(WorkflowInstance.workflow_id == campaign.workflow_id).to_list()
    instance_ids = [i.id for i in instances]
    
    performance = {}
    if instance_ids:
        steps = await WorkflowStep.find(
            In(WorkflowStep.instance_id, instance_ids),
            WorkflowStep.status == "completed"
        ).to_list()
        
        node_stats = {}
        for step in steps:
            if step.finished_at and step.started_at:
                duration = (step.finished_at - step.started_at).total_seconds()
                nid = str(step.node_id)
                if nid not in node_stats:
                    node_stats[nid] = {"total_duration": 0, "executions": 0}
                node_stats[nid]["total_duration"] += duration
                node_stats[nid]["executions"] += 1
                
        for nid, stats in node_stats.items():
            performance[nid] = {
                "avg_duration_seconds": round(stats["total_duration"] / stats["executions"], 2),
                "executions": stats["executions"]
            }

    return {
        "campaign_id": str(campaign_id),
        "name": campaign.name,
        "is_active": campaign.is_active,
        "recent_activity": [
            {
                "id": str(e.id),
                "type": e.type,
                "created_at": e.created_at.isoformat(),
                "data": e.data,
            }
            for e in recent_events
        ],
        "node_performance": performance,
    }


# ── Infrastructure Stats (admin) ──────────────────────────────────────────────

@router.get("/infrastructure", summary="Redis and Celery worker metrics")
async def get_infrastructure_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed Redis and Celery worker metrics."""
    roles = await get_current_user_roles(current_user)
    if not any(r in roles for r in ["admin", "sales_lead"]):
        raise HTTPException(status_code=403, detail="Admin or Sales Lead access required")

    infra_data: Dict[str, Any] = {
        "redis": {"status": "unknown"},
        "celery": {"workers": [], "total_active": 0, "total_scheduled": 0},
    }

    try:
        r = Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        info = r.info()
        infra_data["redis"] = {
            "status": "healthy",
            "memory_usage_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            "connected_clients": info.get("connected_clients", 0),
            "version": info.get("redis_version"),
            "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 1),
        }
    except Exception as e:
        logger.error(f"Failed to fetch Redis infra stats: {e}")
        infra_data["redis"]["status"] = "error"
        infra_data["redis"]["error"] = str(e)

    try:
        from ..celery_app import celery_app
        inspector = celery_app.control.inspect(timeout=2)
        active = inspector.active() or {}
        scheduled = inspector.scheduled() or {}
        registered = inspector.registered() or {}

        workers = []
        for worker_name, tasks in active.items():
            workers.append({
                "name": worker_name,
                "active_tasks": len(tasks),
                "scheduled_tasks": len(scheduled.get(worker_name, [])),
                "registered_tasks": len(registered.get(worker_name, [])),
            })
            infra_data["celery"]["total_active"] += len(tasks)
            infra_data["celery"]["total_scheduled"] += len(scheduled.get(worker_name, []))

        infra_data["celery"]["workers"] = workers
    except Exception as e:
        logger.error(f"Failed to fetch Celery infra stats: {e}")
        infra_data["celery"]["error"] = str(e)

    return infra_data


# DB Pool Stats (MongoDB equivalent)

@router.get("/db-pool", summary="MongoDB connection stats")
async def get_db_pool_stats(
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get MongoDB connection pool and server status stats."""
    if "admin" not in current_admin.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    from ..db import client as motor_client
    warnings_list = []
    pool_info = {}
    config = {}
    utilization_pct = 0.0

    try:
        if motor_client is not None:
            server_status = await motor_client.admin.command("serverStatus")
            connections = server_status.get("connections", {})
            current_conns = connections.get("current", 0)
            available_conns = connections.get("available", 0)
            total_conns = current_conns + available_conns
            utilization_pct = round((current_conns / total_conns * 100), 1) if total_conns > 0 else 0.0

            pool_info = {
                "pool_size": total_conns,
                "checked_in": available_conns,
                "checked_out": current_conns,
                "overflow": 0,
                "invalid": 0
            }
            config = {
                "pool_size": total_conns,
                "max_overflow": 0,
                "pool_recycle_seconds": 0,
                "statement_timeout_ms": 0,
                "lock_timeout_ms": 0
            }

            if utilization_pct > 80:
                warnings_list.append(f"High connection pool usage: {utilization_pct}%")
        else:
            warnings_list.append("MongoDB client is not initialized")
    except Exception as e:
        logger.error(f"Failed to fetch DB pool stats: {e}")
        warnings_list.append(f"Could not retrieve pool stats: {str(e)}")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "pool": pool_info,
        "utilization_pct": utilization_pct,
        "config": config,
        "warnings": warnings_list
    }


# Index Health (MongoDB equivalent)

@router.get("/index-health", summary="MongoDB collection index health")
async def get_index_health(
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get index stats for MongoDB collections as a health check."""
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from ..db import client as motor_client
    indexes = {}
    table_sizes = {}
    missing_indexes = 0
    seq_scan_warnings = []

    collection_names = [
        "users", "campaigns", "workflows", "workflowinstances",
        "workflowsteps", "contacts", "leads", "emailsends", "events"
    ]

    try:
        if motor_client is not None:
            db = motor_client.get_default_database(default="marketing_automation")
            for collection_name in collection_names:
                try:
                    coll = db[collection_name]
                    coll_indexes = await coll.index_information()
                    count = await coll.estimated_document_count()
                    stats = await db.command("collStats", collection_name)

                    indexes[collection_name] = f"{len(coll_indexes)} indexes"
                    table_sizes[collection_name] = {
                        "total_size": f"{round(stats.get('totalSize', 0) / 1024, 1)} KB",
                        "table_size": f"{round(stats.get('size', 0) / 1024, 1)} KB",
                        "row_estimate": count
                    }
                except Exception:
                    indexes[collection_name] = "unavailable"
    except Exception as e:
        logger.error(f"Failed to get index health: {e}")
        seq_scan_warnings.append(f"Could not retrieve index stats: {str(e)}")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "indexes": indexes,
        "missing_indexes": missing_indexes,
        "table_sizes": table_sizes,
        "seq_scan_warnings": seq_scan_warnings,
        "action_needed": seq_scan_warnings[0] if seq_scan_warnings else None
    }
