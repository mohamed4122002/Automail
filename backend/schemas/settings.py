from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

class SettingBase(BaseModel):
    key: str
    value: dict[str, Any]
    category: Optional[str] = None
    description: Optional[str] = None

class SettingCreate(SettingBase):
    is_encrypted: bool = False

class SettingUpdate(BaseModel):
    value: dict[str, Any]

class SettingResponse(SettingBase):
    id: UUID
    is_encrypted: bool
    created_at: datetime
    updated_at: datetime
    updated_by_id: Optional[UUID] = None

    class Config:
        from_attributes = True

class EmailProviderConfig(BaseModel):
    provider: str  # "sendgrid", "ses", "smtp"
    api_key: Optional[str] = None
    from_email: str
    from_name: str
    # SMTP specific
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    # AWS SES specific
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    aws_region: Optional[str] = None

class SystemPreferences(BaseModel):
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    language: str = "en"
    enable_notifications: bool = True

class WorkflowPreferences(BaseModel):
    default_delay_hours: int = 24
    max_retry_attempts: int = 3
    execution_start_hour: int = 9
    execution_end_hour: int = 17
