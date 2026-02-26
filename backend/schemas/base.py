from datetime import datetime
from typing import Optional, Generic, TypeVar
from pydantic import BaseModel, ConfigDict
from uuid import UUID

T = TypeVar("T")

class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class IDSchema(BaseResponse):
    id: UUID

class TimestampSchema(BaseResponse):
    created_at: datetime
    updated_at: datetime

class PaginatedResponse(BaseResponse, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int
