import asyncio
import sys
import os

# Add the project root to sys.path to allow importing the 'backend' package
sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.models import Role
from backend.seed_real_data import seed_real_data
from backend.logging_config import get_logger

logger = get_logger(__name__)

async def seed():
    try:
        await init_db()
        logger.info("Initializing base seed data pack (MongoDB)...")
        
        # 1. Check if roles exist
        # logger.info("Checking database state...")
        # We handle idempotency within seed_real_data.py now

        logger.info("Redirecting to real data seed...")
        await seed_real_data()
        logger.info("Real data seeding complete.")
            
    except Exception as e:
        import traceback
        logger.error(f"Seed script CRASHED: {e}")
        logger.error(traceback.format_exc())
        raise
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(seed())
