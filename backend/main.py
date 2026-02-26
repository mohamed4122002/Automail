from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .logging_config import setup_logging

# Initialize logging
setup_logging()
from .api import auth as auth_api
from .api import campaigns as campaigns_api
from .api import workflows as workflows_api
from .api import events as events_api
from .api import analytics as analytics_api
from .api import realtime as realtime_api
from .api import workflow_runtime as workflow_runtime_api
from .api import templates as templates_api


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,  # Configured via CORS_ORIGINS env var
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter(prefix="/api")
    
    api_router.include_router(auth_api.router)
    api_router.include_router(campaigns_api.router)
    api_router.include_router(workflows_api.router)
    api_router.include_router(events_api.router)
    api_router.include_router(analytics_api.router)
    api_router.include_router(realtime_api.router)
    api_router.include_router(workflow_runtime_api.router)
    
    # New User Router
    from .api import users as users_api
    api_router.include_router(users_api.router)

    # Contacts Router
    from .api import contacts as contacts_api
    api_router.include_router(contacts_api.router)

    # Leads Router
    from .api import leads as leads_api
    api_router.include_router(leads_api.router)

    # Settings Router
    from .api import settings as settings_api
    api_router.include_router(settings_api.router)

    # Retries Router
    from .api import retries as retries_api
    api_router.include_router(retries_api.router)
    api_router.include_router(retries_api.cold_leads_router)

    # Lead Status Router
    from .api import lead_status as lead_status_api
    api_router.include_router(lead_status_api.router)

    # Unsubscribe Router
    from .api import unsubscribe as unsubscribe_api
    api_router.include_router(unsubscribe_api.router)

    # Human Handling Router
    from .api import human_handling as human_handling_api
    api_router.include_router(human_handling_api.router)

    # Notes Router
    from .api import notes as notes_api
    api_router.include_router(notes_api.router)

    # Tracking Router
    from .api import tracking as tracking_api
    api_router.include_router(tracking_api.router)

    # Email Queue Router
    from .api import email_queue as email_queue_api
    api_router.include_router(email_queue_api.router)

    # A/B Testing Router
    from .api import ab_testing as ab_testing_api
    api_router.include_router(ab_testing_api.router)
    api_router.include_router(templates_api.router)

    # Spam Shield Router
    from .api import spam_shield as spam_shield_api
    api_router.include_router(spam_shield_api.router)

    # Monitoring Router
    from .api import monitoring as monitoring_api
    api_router.include_router(monitoring_api.router)

    # System Health Router
    from .api import system as system_api
    api_router.include_router(system_api.router)

    app.include_router(api_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()

