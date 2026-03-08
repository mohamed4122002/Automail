from celery import Celery

from .config import settings


celery_app = Celery(
    "marketing_automation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.tasks", "backend.tasks_lead_status"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "daily-warmup-increase": {
        "task": "process_daily_warmup_increase_task",
        "schedule": crontab(hour=0, minute=0), # Run daily at midnight
    },
    "check-unopened-emails": {
        "task": "check_and_retry_unopened_emails", # Ensure this matches task name
        "schedule": crontab(minute="*/30"), # Every 30 mins
    },
    "check-lead-inactivity": {
        "task": "check_lead_inactivity",
        "schedule": crontab(hour=8, minute=0), # Run every morning at 8 AM
    },
    "sync-email-replies": {
        "task": "sync-email-replies",
        "schedule": crontab(minute="*/30"), # Every 30 mins
    },
    "sync-dashboard-metrics": {
        "task": "sync_dashboard_metrics",
        "schedule": crontab(minute="*/5"), # Every 5 mins
    }
}

