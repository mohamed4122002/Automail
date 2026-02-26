"""
Seed default email provider configuration.
This ensures the system can send emails immediately without manual configuration.
"""
import asyncio
from sqlalchemy import select
from .db import AsyncSessionLocal
from .models import Setting
from .logging_config import get_logger

logger = get_logger(__name__)

async def seed_default_email_provider():
    """Seed default SMTP email provider configuration."""
    async with AsyncSessionLocal() as db:
        # Check if email_provider setting already exists
        result = await db.execute(
            select(Setting).where(Setting.key == "email_provider")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info("✓ Email provider already configured, skipping default seed")
            return
        
        # Create default SMTP configuration
        from .services.settings import SettingsService
        service = SettingsService(db)
        
        default_config = {
            "provider": "smtp",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "happymr412@gmail.com",
            "smtp_password": "refhqkqekxxuiuci",
            "from_email": "happymr412@gmail.com",
            "from_name": "Marketing System",
            "use_tls": True
        }
        
        await service.create_or_update_setting(
            key="email_provider",
            value=default_config,
            category="email",
            is_encrypted=True,
            description="Default SMTP email provider configuration"
        )
        
        logger.info("✓ Default email provider (SMTP/Gmail) configured successfully")

if __name__ == "__main__":
    asyncio.run(seed_default_email_provider())
