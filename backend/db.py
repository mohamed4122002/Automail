from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData, text, event
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from .config import settings
import logging

logger = logging.getLogger(__name__)

# ── Naming conventions ────────────────────────────────────────────────────────
# Helps Alembic generate predictable constraint names
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


def _make_async_url(url: str) -> str:
    """Convert sync PostgreSQL URL to asyncpg driver URL."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url


ASYNC_DATABASE_URL = _make_async_url(str(settings.DATABASE_URL))

# ── FastAPI Engine — WITH connection pooling ──────────────────────────────────
# NullPool is NOT used here. FastAPI is async and long-running, so we maintain
# a pool of persistent connections for performance.
engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    # Pool configuration (tunable via .env)
    poolclass=AsyncAdaptedQueuePool,
    pool_size=settings.DB_POOL_SIZE,          # Persistent connections kept alive
    max_overflow=settings.DB_MAX_OVERFLOW,    # Extra connections allowed under burst
    pool_pre_ping=True,                       # Validate connection before use (handles stale connections)
    pool_recycle=settings.DB_POOL_RECYCLE,    # Recycle connections every hour
    # Query timeouts (prevents runaway queries from holding connections)
    connect_args={
        "server_settings": {
            "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT_MS),
            "lock_timeout": str(settings.DB_LOCK_TIMEOUT_MS),
            "application_name": "marketing_automation_api",
        }
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session from the connection pool."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_pool_status() -> dict:
    """Return current connection pool statistics for monitoring."""
    pool = engine.pool
    try:
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalidated_count() if hasattr(pool, "invalidated_count") else 0,
        }
    except Exception as e:
        logger.warning(f"Could not read pool stats: {e}")
        return {"error": str(e)}


async def check_db_connection() -> bool:
    """Quick connectivity check — used by health endpoint."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"DB connectivity check failed: {e}")
        return False
