from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class RetryConfig(BaseModel):
    enabled: bool = True
    first_retry_hours: int = 48
    second_retry_hours: int = 72
    max_attempts: int = 3

class RetryStats(BaseModel):
    total_sent: int
    total_unopened: int
    pending_first_retry: int
    pending_second_retry: int
    marked_as_cold: int
    
class RetryAttemptDetail(BaseModel):
    id: UUID
    email_send_id: UUID
    user_id: UUID
    user_email: str
    attempt_number: int
    scheduled_for: datetime
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ColdLeadResponse(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    last_email_sent: datetime
    retry_attempts: int
    marked_cold_at: datetime
    
    class Config:
        from_attributes = True
