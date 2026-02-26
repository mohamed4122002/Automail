"""
Enhanced Monitoring API — Phase 1 DB Hardening
Provides health checks, connection pool stats, security status, and index health.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta

from ..db import get_db, get_pool_status, check_db_connection
from ..models import Campaign, User, EmailSend, Event, WorkflowInstance, WorkflowStep
from ..auth import get_current_user
from ..config import settings

from redis import Redis
from ..services.campaign_manager import CampaignManagerService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/monitor", tags=["monitoring"])


# ── Health Check (public) ─────────────────────────────────────────────────────

@router.get("/health", summary="Service health check")
async def health_check(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check health of all services: PostgreSQL, Redis, Celery.
    Returns 200 even if degraded (so frontend can show partial outage UI).
    Returns 503 only if ALL services are down.
    """
    health: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "pool": {},
    }

    # 1. PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health["services"]["postgres"] = "healthy"
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        health["services"]["postgres"] = "unhealthy"
        health["status"] = "degraded"

    # 2. Connection Pool Stats
    try:
        health["pool"] = await get_pool_status()
    except Exception as e:
        health["pool"] = {"error": str(e)}

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


# ── DB Pool Stats (admin) ─────────────────────────────────────────────────────

@router.get("/db-pool", summary="Connection pool statistics")
async def get_db_pool_stats(
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Return real-time connection pool statistics.
    Useful for diagnosing connection exhaustion under load.
    """
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    pool_stats = await get_pool_status()

    # Compute utilization percentage
    pool_size = pool_stats.get("pool_size", 0)
    checked_out = pool_stats.get("checked_out", 0)
    utilization = round((checked_out / pool_size * 100) if pool_size > 0 else 0, 1)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "pool": pool_stats,
        "utilization_pct": utilization,
        "config": {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle_seconds": settings.DB_POOL_RECYCLE,
            "statement_timeout_ms": settings.DB_STATEMENT_TIMEOUT_MS,
            "lock_timeout_ms": settings.DB_LOCK_TIMEOUT_MS,
        },
        "warnings": (
            ["Pool utilization above 80% — consider increasing DB_POOL_SIZE"]
            if utilization > 80 else []
        ),
    }


# ── Security Status (admin) ───────────────────────────────────────────────────

@router.get("/security-status", summary="Security configuration status")
async def get_security_status(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Audit security configuration: encryption, CORS, JWT, and sensitive settings.
    Flags any misconfiguration that could be a security risk.
    """
    if current_admin.role != "admin":
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
            result = await db.execute(
                select(Setting).where(Setting.key == key)
            )
            setting = result.scalar_one_or_none()
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
    db_url_safe = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "hidden"
    checks["db_host"] = db_url_safe

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "ISSUES_FOUND" if issues else "OK",
        "issue_count": len(issues),
        "issues": issues,
        "checks": checks,
    }


# ── Index Health (admin) ──────────────────────────────────────────────────────

@router.get("/index-health", summary="Database index usage statistics")
async def get_index_health(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check if the performance indexes from migration 0010 exist and are being used.
    Also shows table sizes and sequential scan counts.
    """
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check our specific indexes exist
    our_indexes = [
        "ix_events_campaign_type_created",
        "ix_events_email_send_type",
        "ix_events_created_at",
        "ix_events_user_type_created",
        "ix_email_sends_status_created",
        "ix_email_sends_campaign_status",
        "ix_workflow_instances_status_updated",
        "ix_workflow_instances_workflow_status",
        "ix_workflow_steps_instance_status",
        "ix_workflow_steps_node_status",
        "ix_contacts_list_email",
        "ix_leads_status_score",
        "ix_leads_assigned_to",
    ]

    index_status = {}
    try:
        for idx_name in our_indexes:
            result = await db.execute(text(
                "SELECT indexname FROM pg_indexes WHERE indexname = :name"
            ), {"name": idx_name})
            exists = result.scalar_one_or_none() is not None
            index_status[idx_name] = "EXISTS" if exists else "MISSING — run: alembic upgrade head"
    except Exception as e:
        index_status["error"] = str(e)

    # Table sizes
    table_sizes = {}
    try:
        result = await db.execute(text("""
            SELECT
                relname AS table_name,
                pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                pg_size_pretty(pg_relation_size(relid)) AS table_size,
                n_live_tup AS row_estimate
            FROM pg_catalog.pg_statio_user_tables
            WHERE relname IN ('events', 'email_sends', 'workflow_instances', 'workflow_steps', 'contacts', 'leads')
            ORDER BY pg_total_relation_size(relid) DESC
        """))
        for row in result:
            table_sizes[row.table_name] = {
                "total_size": row.total_size,
                "table_size": row.table_size,
                "row_estimate": row.row_estimate,
            }
    except Exception as e:
        table_sizes["error"] = str(e)

    # Sequential scan warnings (tables with high seq scans = missing indexes)
    seq_scan_warnings = []
    try:
        result = await db.execute(text("""
            SELECT relname, seq_scan, idx_scan
            FROM pg_stat_user_tables
            WHERE relname IN ('events', 'email_sends', 'workflow_instances')
              AND seq_scan > 100
            ORDER BY seq_scan DESC
        """))
        for row in result:
            if row.seq_scan > (row.idx_scan or 0):
                seq_scan_warnings.append(
                    f"Table '{row.relname}': {row.seq_scan} seq scans vs {row.idx_scan} index scans — check indexes"
                )
    except Exception as e:
        seq_scan_warnings.append(f"Could not check seq scans: {e}")

    missing_count = sum(1 for v in index_status.values() if "MISSING" in str(v))

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "indexes": index_status,
        "missing_indexes": missing_count,
        "table_sizes": table_sizes,
        "seq_scan_warnings": seq_scan_warnings,
        "action_needed": "Run `alembic upgrade head` to create missing indexes" if missing_count > 0 else None,
    }


# ── System Stats (admin) ──────────────────────────────────────────────────────

@router.get("/system", summary="System-wide metrics")
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get system-wide metrics and health status."""
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    campaign_count = (await db.execute(select(func.count(Campaign.id)))).scalar()
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    sent_count = (await db.execute(select(func.count(EmailSend.id)).where(EmailSend.status == "sent"))).scalar()
    queued_count = (await db.execute(select(func.count(EmailSend.id)).where(EmailSend.status == "queued"))).scalar()

    active_workflows = (await db.execute(
        select(func.count(WorkflowInstance.id)).where(WorkflowInstance.status == "running")
    )).scalar()

    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_events_count = (await db.execute(
        select(func.count(Event.id)).where(Event.created_at >= yesterday)
    )).scalar()

    pool_stats = await get_pool_status()

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
        },
        "pool": pool_stats,
    }


# ── Workflow Health (admin) ───────────────────────────────────────────────────

@router.get("/workflow/health", summary="Workflow instance health")
async def get_workflow_health(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    """Get metrics on workflow instances and stalled detections."""
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    service = CampaignManagerService(db)
    return await service.get_workflow_health()


@router.post("/workflow/repair", summary="Repair stalled workflows")
async def repair_stalled_workflows(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
):
    """Trigger a repair for all stalled workflow instances."""
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    service = CampaignManagerService(db)
    return await service.repair_stalled_instances()


# ── Campaign Monitoring (admin) ───────────────────────────────────────────────

@router.get("/campaign/{campaign_id}", summary="Campaign monitoring detail")
async def get_campaign_monitoring(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed monitoring for a specific campaign."""
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    campaign = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recent_events_res = await db.execute(
        select(Event)
        .where(Event.campaign_id == campaign_id)
        .order_by(desc(Event.created_at))
        .limit(20)
    )
    recent_events = recent_events_res.scalars().all()

    perf_res = await db.execute(
        select(
            WorkflowStep.node_id,
            func.avg(
                func.extract("epoch", WorkflowStep.finished_at) -
                func.extract("epoch", WorkflowStep.started_at)
            ).label("avg_duration"),
            func.count(WorkflowStep.id).label("executions")
        )
        .join(WorkflowInstance, WorkflowStep.instance_id == WorkflowInstance.id)
        .where(WorkflowInstance.workflow_id == campaign.workflow_id)
        .where(WorkflowStep.status == "completed")
        .where(WorkflowStep.finished_at != None)
        .group_by(WorkflowStep.node_id)
    )
    performance = {
        str(row.node_id): {
            "avg_duration_seconds": round(float(row.avg_duration), 2) if row.avg_duration else 0,
            "executions": row.executions,
        }
        for row in perf_res if row.node_id
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
    current_admin: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed Redis and Celery worker metrics."""
    if current_admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

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
