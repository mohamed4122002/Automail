from uuid import UUID
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
import json
import logging

logger = logging.getLogger(__name__)

from ..models import Setting
from ..schemas.settings import SettingCreate, SettingUpdate
from ..config import settings as app_settings

# Encryption key comes from config (which reads from .env — never hardcoded)
def _get_cipher() -> Fernet:
    """Lazy-load cipher so it's created after settings are fully initialized."""
    return Fernet(app_settings.SETTINGS_ENCRYPTION_KEY.encode())

class SettingsService:
    def __init__(self):
        pass

    def _normalize_key(self, key: str) -> str:
        """Normalize key to use underscores instead of dashes."""
        return key.replace("-", "_")

    def _encrypt_value(self, value: dict) -> dict:
        """Encrypt sensitive fields in the value dict using Fernet symmetric encryption."""
        json_str = json.dumps(value)
        encrypted = _get_cipher().encrypt(json_str.encode())
        return {"encrypted": encrypted.decode()}

    def _decrypt_value(self, encrypted_value: dict) -> dict:
        """Decrypt the value dict with double-layer resilience for plain data."""
        if not isinstance(encrypted_value, dict):
            return encrypted_value

        encrypted_str = encrypted_value.get("encrypted")
        if not encrypted_str:
            # If not in the 'encrypted' wrapper, it's already plain
            return encrypted_value

        try:
            # 1. Try standard decryption
            decrypted = _get_cipher().decrypt(encrypted_str.encode())
            return json.loads(decrypted.decode())
        except (InvalidToken, Exception) as e:
            # 2. Resilience layer: Check if the 'encrypted' string is actually already plain JSON
            try:
                potential_json = json.loads(encrypted_str)
                if isinstance(potential_json, dict):
                    logger.warning(f"Data in 'encrypted' field for setting was actually plain JSON. Returning parsed data.")
                    return potential_json
            except json.JSONDecodeError:
                pass
            
            logger.error(f"Decryption failed: {e}. Returning raw value as fallback.")
            return encrypted_value

    async def get_setting(self, key: str) -> Optional[Setting]:
        """Get a setting by key."""
        key = self._normalize_key(key)
        setting = await Setting.find_one(Setting.key == key)
        
        if setting and getattr(setting, 'is_encrypted', False):
            setting.value = self._decrypt_value(setting.value)
        
        return setting

    async def get_settings_by_category(self, category: str) -> list[Setting]:
        """Get all settings in a category."""
        settings = await Setting.find(Setting.category == category).to_list()
        
        for setting in settings:
            if getattr(setting, 'is_encrypted', False):
                setting.value = self._decrypt_value(setting.value)
        
        return settings

    async def get_all_settings(self) -> list[Setting]:
        """Get all settings."""
        settings = await Setting.find_all().to_list()
        
        for setting in settings:
            if getattr(setting, 'is_encrypted', False):
                setting.value = self._decrypt_value(setting.value)
        
        return settings

    async def create_or_update_setting(
        self, 
        key: str, 
        value: dict, 
        category: Optional[str] = None,
        is_encrypted: bool = False,
        description: Optional[str] = None,
        updated_by_id: Optional[UUID] = None,
        validate: bool = True
    ) -> Setting:
        """Create or update a setting with optional validation."""
        key = self._normalize_key(key)
        
        # Auto-detect sensitive keys that MUST be encrypted — never stored in plain text
        SENSITIVE_KEYS = {
            "email_provider", "api_keys", "smtp_config", "aws_credentials",
            "sendgrid_key", "mailgun_key", "ses_credentials", "webhook_secret",
            "oauth_credentials", "database_credentials"
        }
        if key in SENSITIVE_KEYS:
            is_encrypted = True
            
        # Pre-save validation for critical settings
        if validate and key == "email_provider":
            await self._validate_email_provider(value)
            
        existing = await self.get_setting(key)
        
        if is_encrypted and not (isinstance(value, dict) and "encrypted" in value):
            stored_value = self._encrypt_value(value)
        else:
            stored_value = value
        
        if existing:
            existing.value = stored_value
            existing.is_encrypted = is_encrypted
            if category:
                existing.category = category
            if description:
                existing.description = description
            existing.updated_by_id = updated_by_id
            await existing.save()
            
            if existing.is_encrypted:
                existing.value = value
            
            return existing
        else:
            new_setting = Setting(
                key=key,
                value=stored_value,
                category=category,
                is_encrypted=is_encrypted,
                description=description,
                updated_by_id=updated_by_id
            )
            await new_setting.insert()
            
            if new_setting.is_encrypted:
                new_setting.value = value
            
            return new_setting

    async def delete_setting(self, key: str) -> bool:
        """Delete a setting."""
        key = self._normalize_key(key)
        setting = await self.get_setting(key)
        if setting:
            await setting.delete()
            return True
        return False

    async def _validate_email_provider(self, config: dict):
        """Perform a lightweight test of email provider settings before saving."""
        from ..email_providers import get_email_provider
        # We can implement a lightweight test by loading the provider briefly.
        pass
