from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import liquid

from ..db import get_db
from ..models import EmailTemplate
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/templates", tags=["templates"])

# Pydantic Schemas
class TemplateBase(BaseModel):
    name: str
    subject: str
    html_body: str

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    html_body: Optional[str] = None

class TemplateResponse(TemplateBase):
    id: UUID

    class Config:
        from_attributes = True

class PreviewRequest(BaseModel):
    html_body: str
    test_data: Dict[str, Any]

class PreviewResponse(BaseModel):
    rendered_html: str

@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all available email templates."""
    result = await db.execute(select(EmailTemplate))
    return result.scalars().all()

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get a specific template by ID."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.post("", response_model=TemplateResponse)
async def create_template(
    template_in: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new email template."""
    template = EmailTemplate(
        id=uuid4(),
        name=template_in.name,
        subject=template_in.subject,
        html_body=template_in.html_body
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    template_in: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update an existing template."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = template_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    return template

@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete a template."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await db.delete(template)
    await db.commit()
    return {"status": "success"}

@router.post("/preview", response_model=PreviewResponse)
async def preview_template(
    request: PreviewRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Render a Liquid template with provided test data.
    Used for the frontend preview pane.
    """
    try:
        template = liquid.Template(request.html_body)
        rendered = template.render(**request.test_data)
        return {"rendered_html": rendered}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Liquid Template Rendering Error: {str(e)}")
