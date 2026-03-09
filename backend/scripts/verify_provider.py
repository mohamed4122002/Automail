import sys
import os
import asyncio

# Ensure backend matches the path structure
sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.email_providers import get_email_provider

async def verify():
    print("Initializing MongoDB connection...")
    try:
        await init_db()
        print("Database initialized. Requesting email provider...")
        provider = await get_email_provider()
        
        if provider:
            print(f"✅ Provider initialized safely: {type(provider).__name__}")
        else:
            print("❌ Failed to initialize provider")
            sys.exit(1)
    finally:
        await close_db()

if __name__ == "__main__":
    print("Starting Provider Safety Verification...")
    try:
        asyncio.run(verify())
        print("✅ Verification Complete")
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        sys.exit(1)
