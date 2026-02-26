import asyncio
from datetime import datetime, timedelta
import uuid
import sqlalchemy as sa
from .auth import get_password_hash
from .db import AsyncSessionLocal
from .models import (
    Campaign,
    EmailTemplate,
    Event,
    LeadScore,
    Pipeline,
    PipelineItem,
    Role,
    User,
    UserRole,
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    UserNote,
    ContactList,
    Contact,
    LeadStatusEnum,
)
from .seed_real_data import seed_real_data
from .logging_config import get_logger

logger = get_logger(__name__)

async def seed():
    try:
        logger.info("Initializing base seed data...")
        async with AsyncSessionLocal() as db:
            # 1. Check if roles exist
            res_roles = await db.execute(sa.select(sa.func.count()).select_from(Role))
            if int(res_roles.scalar_one()) > 0:
                logger.info("Database seems initialized. Skipping seeding.")
                return

            logger.info("Redirecting to real data seed...")
            await seed_real_data()
            logger.info("Real data seeding complete.")
            
    except Exception as e:
        import traceback
        logger.error(f"Seed script CRASHED: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    asyncio.run(seed())
