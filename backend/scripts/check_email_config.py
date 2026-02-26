import asyncio
from backend.core.db import task_context
from backend.services.settings import SettingsService
from backend.email_providers import get_email_provider

async def check_provider():
    async with task_context() as db:
        service = SettingsService(db)
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
        
        provider = await get_email_provider(db)
        print(f"Active Provider Instance: {type(provider).__name__}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(check_provider())
