import asyncio
import sys
import logging
from sqlalchemy import text
from redis import Redis
from backend.db import AsyncSessionLocal
from backend.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_postgres():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL: HEALTHY")
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL: UNHEALTHY ({e})")
        return False

def check_redis():
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        r.ping()
        logger.info("✅ Redis: HEALTHY")
        return True
    except Exception as e:
        logger.error(f"❌ Redis: UNHEALTHY ({e})")
        return False

async def check_celery():
    try:
        from backend.celery_app import celery_app
        inspector = celery_app.control.inspect()
        active = inspector.active()
        if active:
            logger.info(f"✅ Celery: HEALTHY ({len(active)} workers online)")
            return True
        else:
            logger.warning("⚠️ Celery: DEGRADED (No active workers found)")
            return False
    except Exception as e:
        logger.error(f"❌ Celery: UNHEALTHY ({e})")
        return False

async def main():
    logger.info("🔍 Starting System Health Check...")
    
    results = await asyncio.gather(
        check_postgres(),
        asyncio.to_thread(check_redis),
        check_celery()
    )
    
    if all(results):
        logger.info("🚀 SYSTEM STATUS: ALL SERVICES OPERATIONAL")
        sys.exit(0)
    else:
        logger.error("🛑 SYSTEM STATUS: DEGRADED OR UNHEALTHY")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
