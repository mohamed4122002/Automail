import asyncio

def run_async(coro):
    """
    Runs an async coroutine in a dedicated event loop
    that is safe for Celery workers.
    """
    async def _wrapped(coro):
        from ..db import init_db
        # We need check_db_connection or checking if client is init
        try:
            from beanie import document
            # If a model doesn't have a database, Beanie is not initialized.
            from ..models import User
            User.get_motor_collection()
        except BaseException:
            # We must initialize DB
            await init_db()
        return await coro

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_wrapped(coro))
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
