import asyncio
import logging
from sqlalchemy import text
from backend.db import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    logger.info("Starting migration to add started_at and finished_at to workflow_steps...")
    async with AsyncSessionLocal() as session:
        try:
            # Check if columns exist first (PostgreSQL specific way)
            res = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='workflow_steps' AND column_name='started_at';
            """))
            if not res.scalar():
                logger.info("Adding started_at column...")
                await session.execute(text("ALTER TABLE workflow_steps ADD COLUMN started_at TIMESTAMP WITHOUT TIME ZONE;"))
            
            res = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='workflow_steps' AND column_name='finished_at';
            """))
            if not res.scalar():
                logger.info("Adding finished_at column...")
                await session.execute(text("ALTER TABLE workflow_steps ADD COLUMN finished_at TIMESTAMP WITHOUT TIME ZONE;"))
            
            await session.commit()
            logger.info("Migration completed successfully.")
        except Exception as e:
            await session.rollback()
            logger.error(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate())
