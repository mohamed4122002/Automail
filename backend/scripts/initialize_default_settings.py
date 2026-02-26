import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.config import settings
from backend.services.settings import SettingsService

async def init_defaults():
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(url)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        service = SettingsService(db)
        
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

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_defaults())
