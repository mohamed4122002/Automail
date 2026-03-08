from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import logging
from .config import settings

logger = logging.getLogger(__name__)

# Global motor client
client: AsyncIOMotorClient = None

async def init_db():
    """Initialize MongoDB connection and Beanie ODM."""
    global client
    try:
        logger.info("Connecting to MongoDB...")
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            minPoolSize=10,
            maxPoolSize=100,
            waitQueueTimeoutMS=5000
        )
        
        # We need to import all Beanie documents here for initialization
        from .models import __beanie_models__
        
        # The provided mongodb URL contains the default database to use
        db = client.get_default_database(default="marketing_automation")
        
        await init_beanie(database=db, document_models=__beanie_models__)
        logger.info("MongoDB & Beanie initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed.")

async def check_db_connection() -> bool:
    """Quick connectivity check — used by health endpoint."""
    try:
        if client is not None:
            await client.admin.command('ping')
            return True
        return False
    except Exception as e:
        logger.error(f"DB connectivity check failed: {e}")
        return False
