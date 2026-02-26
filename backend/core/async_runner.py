import asyncio

def run_async(coro):
    """
    Runs an async coroutine in a dedicated event loop
    that is safe for Celery workers.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
