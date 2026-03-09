import asyncio
import logging
from backend.db import init_db, close_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def wait_for_db():
    """Wait for the database to be ready."""
    logger.info("Waiting for database connection...")
    for i in range(60):
        try:
            # init_db will raise an exception if MongoDB is not available
            await init_db()
            logger.info("Database is ready.")
            await close_db()
            return
        except Exception as e:
            if i % 5 == 0:
                logger.info(f"Database unavailable, retrying ({i+1}/60)... error: {e}")
            await asyncio.sleep(1)
    raise Exception("Database not available after 60 seconds.")

if __name__ == "__main__":
    asyncio.run(wait_for_db())
