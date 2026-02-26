import sys
import os
import asyncio

# Ensure backend matches the path structure
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.async_runner import run_async
from backend.email_providers import get_email_provider
from backend.core.db import task_context

async def verify():
    print("Initializing task context...")
    async with task_context() as db:
        print("Task context active. Requesting email provider...")
        provider = await get_email_provider(db)
        
        if provider:
            print(f"✅ Provider initialized safely: {type(provider).__name__}")
        else:
            print("❌ Failed to initialize provider")
            sys.exit(1)

if __name__ == "__main__":
    print("Starting Provider Safety Verification...")
    try:
        run_async(verify())
        print("✅ Verification Complete")
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        sys.exit(1)
