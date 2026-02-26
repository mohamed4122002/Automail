from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from .base import IDSchema, TimestampSchema

class ContactListBase(BaseModel):
    name: str
    description: Optional[str] = None

class ContactListCreate(ContactListBase):
    pass

class ContactListResponse(ContactListBase, IDSchema, TimestampSchema):
    owner_id: UUID
    contact_count: int = 0

class ContactBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    attributes: dict = {}

class ContactCreate(ContactBase):
    pass

class ContactResponse(ContactBase, IDSchema, TimestampSchema):
    contact_list_id: UUID

class ImportResponse(BaseModel):
    task_id: str
    message: str
