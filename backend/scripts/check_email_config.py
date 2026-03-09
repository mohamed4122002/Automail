import asyncio
import sys
import os

sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.services.settings import SettingsService
from backend.email_providers import get_email_provider

async def check_provider():
    try:
        await init_db()
        service = SettingsService() # SettingsService no longer needs db session passed in
        setting = await service.get_setting("email_provider")
        
        print("-" * 50)
        if setting:
            print(f"Setting found: {setting.key}")
            print(f"Is Encrypted: {setting.is_encrypted}")
            # Note: setting.value should already be decrypted by service
            val = setting.value
            print(f"Provider Type: {val.get('provider')}")
            # Mask sensitive info
            masked_val = {k: ("***" if k in ["api_key", "smtp_password", "aws_secret_key"] else v) for k, v in val.items()}
            print(f"Config: {masked_val}")
        else:
            print("Setting 'email_provider' NOT FOUND in database.")
        
        provider = await get_email_provider() # get_email_provider no longer needs db session
        print(f"Active Provider Instance: {type(provider).__name__}")
        print("-" * 50)
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(check_provider())
