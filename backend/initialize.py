import asyncio
import logging
from sqlalchemy import text
from backend.db import AsyncSessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def wait_for_db():
    """Wait for the database to be ready."""
    logger.info("Waiting for database connection...")
    for i in range(60):
        try:
            async with AsyncSessionLocal() as session:
                # Basic check to see if we can talk to the database
                await session.execute(text("SELECT 1"))
            logger.info("Database is ready.")
            return
        except Exception as e:
            await asyncio.sleep(1)
            if i % 5 == 0:
                logger.info(f"Database unavailable, retrying ({i+1}/60)...")
    raise Exception("Database not available after 60 seconds.")

if __name__ == "__main__":
    asyncio.run(wait_for_db())
