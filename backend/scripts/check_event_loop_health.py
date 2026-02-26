import asyncio
import sys
import os
from pprint import pprint

# Ensure backend matches the path structure
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

async def check_health():
    print("=== Event Loop Health Check ===")
    
    try:
        loop = asyncio.get_running_loop()
        print(f"✅ Running loop detected: {loop}")
        print(f"Loop implementation: {type(loop)}")
    except RuntimeError:
        print("❌ No running loop detected!")
        return

    print("\n=== Global Object Audit ===")
    try:
        from backend.db import AsyncSessionLocal, engine
        print(f"Global Engine: {engine}")
        print(f"Global Session Factory: {AsyncSessionLocal}")
    except ImportError:
        print("Could not import global DB objects (Good if we want to avoid them?)")

    print("\n=== Email Provider Check ===")
    try:
        from backend.email_providers import get_email_provider
        from backend.core.db import task_context
        
        async with task_context() as db:
            provider = await get_email_provider(db)
            print(f"✅ Provider initialized in task context: {type(provider).__name__}")
    except Exception as e:
        print(f"❌ Provider check failed: {e}")

if __name__ == "__main__":
    from backend.core.async_runner import run_async
    try:
        run_async(check_health())
    except Exception as e:
        print(f"Health check failed: {e}")
