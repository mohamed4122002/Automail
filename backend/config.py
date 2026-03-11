import os
from functools import lru_cache
from typing import List
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application settings. All secrets MUST come from environment variables."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Prioritize .env file OVER system environment variables
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

    # Core
    APP_NAME: str = "Marketing Automation Platform"
    ENV: str = "development"

    # ── Database ──────────────────────────────────────────────────────────────
    # No default — will raise a clear error if not set in .env
    MONGODB_URL: str

    # ── Security ──────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Fernet key for encrypting sensitive settings (email provider, API keys, etc.)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    SETTINGS_ENCRYPTION_KEY: str

    # ── Default Admin ─────────────────────────────────────────────────────────
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins. Use "*" only in development.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Celery / Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL

    # ── Email ─────────────────────────────────────────────────────────────────
    EMAIL_FROM_DEFAULT: str = "no-reply@example.com"
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("MONGODB_URL", mode="before")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "MONGODB_URL is required. Add it to your .env file.\n"
                "Example: MONGODB_URL=mongodb://questioner_mongodb:27017/marketing_db"
            )
        return v

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v:
            raise ValueError("JWT_SECRET_KEY is required. Generate with: python -c \"import secrets; print(secrets.token_hex(32))\"")
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
        return v

    @field_validator("SETTINGS_ENCRYPTION_KEY", mode="before")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "SETTINGS_ENCRYPTION_KEY is required.\n"
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENV.lower() == "production":
            if "localhost" in self.MONGODB_URL or "127.0.0.1" in self.MONGODB_URL:
                raise ValueError("SECURITY: MONGODB_URL points to localhost in production!")
            if self.CORS_ORIGINS == "*":
                raise ValueError("SECURITY: CORS_ORIGINS cannot be '*' in production!")
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
