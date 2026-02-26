from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional, Dict
import csv
import io
import re
import dns.resolver

from ..db import get_db
from ..models import Contact, ContactList, User
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactValidationResult(BaseModel):
    email: str
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    is_duplicate: bool = False


class ImportPreviewResponse(BaseModel):
    total_rows: int
    valid_count: int
    invalid_count: int
    duplicate_count: int
    contacts: List[ContactValidationResult]


class ImportConfirmRequest(BaseModel):
    contact_list_id: UUID
    file_id: Optional[str] = None # For background processing
    mapping: Dict[str, str] # e.g. {"Email": "csv_col_1", "First Name": "csv_col_2"}
    skip_invalid: bool = True
    skip_duplicates: bool = True


class ContactListCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


def validate_email_format(email: str) -> tuple[bool, List[str]]:
    """Validate email format using regex."""
    errors = []
    
    # Basic format check
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        errors.append("Invalid email format")
        return False, errors
    
    # Check for common issues
    if '..' in email:
        errors.append("Email contains consecutive dots")
    
    if email.startswith('.') or email.endswith('.'):
        errors.append("Email starts or ends with a dot")
    
    local, domain = email.rsplit('@', 1)
    
    if len(local) > 64:
        errors.append("Local part exceeds 64 characters")
    
    if len(domain) > 255:
        errors.append("Domain exceeds 255 characters")
    
    return len(errors) == 0, errors


async def validate_email_dns(email: str) -> tuple[bool, List[str]]:
    """Validate email domain has MX records (DNS check)."""
    warnings = []
    
    try:
        domain = email.split('@')[1]
        
        # Check MX records
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if not mx_records:
                warnings.append("No MX records found for domain")
                return False, warnings
        except dns.resolver.NXDOMAIN:
            warnings.append("Domain does not exist")
            return False, warnings
        except dns.resolver.NoAnswer:
            warnings.append("No MX records found")
            return False, warnings
        except Exception as e:
            warnings.append(f"DNS check failed: {str(e)}")
            return False, warnings
        
        return True, []
        
    except Exception as e:
        warnings.append(f"DNS validation error: {str(e)}")
        return False, warnings


async def check_duplicate(db: AsyncSession, email: str, contact_list_id: Optional[UUID] = None) -> bool:
    """Check if email already exists in database."""
    
    if contact_list_id:
        # Check within specific contact list
        q = await db.execute(
            select(Contact).where(
                Contact.email == email.lower(),
                Contact.contact_list_id == contact_list_id
            )
        )
    else:
        # Check globally
        q = await db.execute(
            select(Contact).where(Contact.email == email.lower())
        )
    
    return q.scalar_one_or_none() is not None


@router.get("/lists")
async def list_contact_lists(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all contact lists for the current user."""
    
    q = await db.execute(
        select(
            ContactList,
            func.count(Contact.id).label("contact_count")
        )
        .outerjoin(Contact, ContactList.id == Contact.contact_list_id)
        .where(ContactList.owner_id == user_id)
        .group_by(ContactList.id)
    )
    results = q.all()
    
    return [
        {
            "id": str(cl.id),
            "name": cl.name,
            "description": cl.description,
            "created_at": cl.created_at.isoformat(),
            "contact_count": count
        }
        for cl, count in results
    ]


@router.post("/lists", status_code=201)
async def create_contact_list(
    request: ContactListCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new contact list."""
    
    contact_list = ContactList(
        name=request.name,
        description=request.description,
        owner_id=user_id
    )
    
    db.add(contact_list)
    await db.commit()
    await db.refresh(contact_list)
    
    return {
        "id": str(contact_list.id),
        "name": contact_list.name,
        "description": contact_list.description
    }


@router.post("/import/headers")
async def get_csv_headers(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Extract headers and first few rows for mapping."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Received file upload: {file.filename}, content_type: {file.content_type}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
            
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        contents = await file.read()
        logger.info(f"Read {len(contents)} bytes from file")
        
        csv_str = contents.decode('utf-8')
        csv_data = io.StringIO(csv_str)
        reader = csv.DictReader(csv_data)
        
        headers = reader.fieldnames or []
        logger.info(f"Extracted headers: {headers}")
        
        sample_rows = []
        for i, row in enumerate(reader):
            if i >= 5: break
            sample_rows.append(row)
        
        logger.info(f"Extracted {len(sample_rows)} sample rows")
            
        import uuid as uuid_pkg
        file_id = f"import_tmp_{uuid_pkg.uuid4()}"
        
        try:
            from ..config import settings
            from redis import Redis
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis.setex(file_id, 3600, csv_str)
            logger.info(f"Stored CSV in Redis with ID: {file_id}")
        except Exception as redis_error:
            logger.error(f"Redis error: {redis_error}")
            raise HTTPException(status_code=500, detail=f"Failed to store file data: {str(redis_error)}")
        
        return {
            "file_id": file_id,
            "headers": headers,
            "sample": sample_rows
        }
    except UnicodeDecodeError as e:
        logger.error(f"UTF-8 decode error: {e}")
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
    except Exception as e:
        logger.error(f"Unexpected error in get_csv_headers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/import/confirm")
async def confirm_import(
    request: ImportConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Confirm and execute the import asynchronously."""
    from ..tasks import import_contacts_task
    
    # Trigger Celery task
    task = import_contacts_task.delay(
        contact_list_id=str(request.contact_list_id),
        file_id=request.file_id,
        mapping=request.mapping,
        skip_invalid=request.skip_invalid,
        skip_duplicates=request.skip_duplicates,
        owner_id=str(user_id)
    )
    
    return {
        "task_id": task.id,
        "status": "queued"
    }

@router.get("/import/status/{task_id}")
async def get_import_status(task_id: str):
    """Check background import task status."""
    from ..celery_app import celery_app
    res = celery_app.AsyncResult(task_id)
    
    if res.ready():
        if res.failed():
            return {"status": "failed", "error": str(res.result)}
        
        # res.result is the dict returned by the task
        result = res.result if isinstance(res.result, dict) else {}
        return {
            "status": "completed",
            "progress": 100,
            "imported": result.get("imported", 0),
            "skipped": result.get("skipped", 0),
            "duplicates": result.get("duplicates", 0),
            "total": result.get("total", 0)
        }
    
    # Progress meta data
    info = res.info if isinstance(res.info, dict) else {}
    return {
        "status": res.status, # PENDING, STARTED, etc.
        "progress": info.get("progress", 0),
        "imported": info.get("imported", 0),
        "skipped": info.get("skipped", 0),
        "duplicates": info.get("duplicates", 0)
    }


@router.get("/lists/{list_id}/contacts")
async def get_contacts_in_list(
    list_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all contacts in a specific list."""
    
    q = await db.execute(
        select(Contact).where(Contact.contact_list_id == list_id)
    )
    contacts = q.scalars().all()
    
    return [
        {
            "id": str(c.id),
            "email": c.email,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "created_at": c.created_at.isoformat()
        }
        for c in contacts
    ]
