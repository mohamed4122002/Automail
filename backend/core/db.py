from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

@asynccontextmanager
async def task_context():
    """
    Context manager for Celery tasks to handle database engine lifecycle.
    
    Creates a fresh AsyncEngine and AsyncSession for the duration of the context.
    This is CRITICAL for preventing event loop conflicts, as asyncpg connections
    are tied to the loop they were created in.
    """

    from ..db import ASYNC_DATABASE_URL
    
    # Create a fresh engine for this task/loop
    # Use NullPool to prevent connection pooling issues with Celery fork/asyncio
    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    try:
        async with session_factory() as db:
            yield db
    finally:
        # Dispose of the engine to close connections and cleanup
        await engine.dispose()
