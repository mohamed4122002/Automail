import asyncio
import sys
import os
from pprint import pprint

# Ensure backend matches the path structure
sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.email_providers import get_email_provider

async def check_health():
    print("=== Event Loop Health Check ===")
    
    try:
        loop = asyncio.get_running_loop()
        print(f"✅ Running loop detected: {loop}")
        print(f"Loop implementation: {type(loop)}")
    except RuntimeError:
        print("❌ No running loop detected!")
        return

    print("\n=== Database Connection Check ===")
    try:
        await init_db()
        from backend.db import check_db_connection
        is_connected = await check_db_connection()
        print(f"✅ MongoDB Connection Check: {'Success' if is_connected else 'Failed'}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

    print("\n=== Email Provider Check ===")
    try:
        provider = await get_email_provider()
        print(f"✅ Provider initialized: {type(provider).__name__}")
    except Exception as e:
        print(f"❌ Provider check failed: {e}")
    finally:
        await close_db()

if __name__ == "__main__":
    try:
        asyncio.run(check_health())
    except Exception as e:
        print(f"Health check failed: {e}")
