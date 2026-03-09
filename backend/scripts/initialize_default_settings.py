import asyncio
import sys
import os

# Add the project root to sys.path to allow importing the 'backend' package
sys.path.append(os.getcwd())

from backend.db import init_db, close_db
from backend.services.settings import SettingsService

async def init_defaults():
    await init_db()
    try:
        service = SettingsService()
        
        # Default SMTP configuration found in frontend
        default_config = {
            "provider": "smtp",
            "from_email": "happymr412@gmail.com",
            "from_name": "Marketing System",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "happymr412@gmail.com",
            "smtp_password": "refhqkqekxxuiuci",
            "use_tls": True
        }
        
        print(f"Applying default email_provider configuration...")
        await service.create_or_update_setting(
            key="email_provider",
            value=default_config,
            category="email",
            is_encrypted=True,
            description="Default Gmail SMTP configuration"
        )
        print("SUCCESS: Default configuration applied.")
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(init_defaults())
