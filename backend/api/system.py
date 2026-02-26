"""
System health and monitoring endpoints.
Provides real-time status of backend services, Celery workers, database, and Redis.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
from typing import Dict, Any
from datetime import datetime

from ..db import get_db
from ..celery_app import celery_app
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def get_system_health(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive system health check.
    Returns status of all critical components.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # 1. Database Health
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        health_status["components"]["database"] = {
            "status": "healthy",
            "type": "postgresql",
            "url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "configured"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # 2. Redis Health
    try:
        from redis import Redis
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "url": settings.REDIS_URL
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # 3. Celery Workers Health
    try:
        from ..celery_app import celery_app
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            health_status["components"]["celery_workers"] = {
                "status": "healthy",
                "worker_count": len(active_workers.keys()),
                "workers": list(active_workers.keys())
            }
        else:
            health_status["components"]["celery_workers"] = {
                "status": "unhealthy",
                "error": "No active workers found"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        health_status["components"]["celery_workers"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # 4. Encryption Health
    try:
        from ..services.settings import ENCRYPTION_KEY
        import base64
        import os
        key_bytes = base64.urlsafe_b64decode(ENCRYPTION_KEY)
        health_status["components"]["encryption"] = {
            "status": "healthy",
            "key_length": len(key_bytes),
            "algorithm": "Fernet (AES-128-CBC)"
        }
    except Exception as e:
        logger.error(f"Encryption health check failed: {e}")
        health_status["components"]["encryption"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # 5. Environment Info
    health_status["environment"] = {
        "app_name": settings.APP_NAME,
        "debug_mode": os.getenv("DEBUG", "false").lower() == "true",
        "log_format": os.getenv("LOG_FORMAT", "standard")
    }
    
    return health_status


@router.get("/workers")
async def get_worker_status() -> Dict[str, Any]:
    """
    Detailed Celery worker status and statistics.
    """
    try:
        inspect = celery_app.control.inspect()
        
        # Get various worker information
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()
        stats = inspect.stats()
        registered_tasks = inspect.registered()
        
        worker_details = {}
        
        if stats:
            for worker_name, worker_stats in stats.items():
                worker_details[worker_name] = {
                    "status": "online",
                    "stats": worker_stats,
                    "active_tasks": len(active_tasks.get(worker_name, [])) if active_tasks else 0,
                    "scheduled_tasks": len(scheduled_tasks.get(worker_name, [])) if scheduled_tasks else 0,
                    "reserved_tasks": len(reserved_tasks.get(worker_name, [])) if reserved_tasks else 0,
                    "registered_tasks": registered_tasks.get(worker_name, []) if registered_tasks else []
                }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "worker_count": len(worker_details),
            "workers": worker_details,
            "has_active_workers": len(worker_details) > 0
        }
    except Exception as e:
        logger.error(f"Failed to get worker status: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "worker_count": 0,
            "workers": {},
            "has_active_workers": False,
            "error": str(e)
        }


@router.get("/tasks/stats")
async def get_task_statistics() -> Dict[str, Any]:
    """
    Get statistics about task execution.
    """
    try:
        inspect = celery_app.control.inspect()
        
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
        
        total_active = sum(len(tasks) for tasks in active.values())
        total_scheduled = sum(len(tasks) for tasks in scheduled.values())
        total_reserved = sum(len(tasks) for tasks in reserved.values())
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_tasks": total_active,
            "scheduled_tasks": total_scheduled,
            "reserved_tasks": total_reserved,
            "total_pending": total_active + total_scheduled + total_reserved
        }
    except Exception as e:
        logger.error(f"Failed to get task statistics: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
