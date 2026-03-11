from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import liquid

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
    user_id: UUID = Depends(get_current_user_id)
):
    """List all available email templates.

    We only need the ID, name and subject in the overview screen –
    the HTML body is large and only required when editing a single
    template.  Using a projection reduces document size and memory
    pressure for large template collections.
    """
    # note: Beanie's `project` accepts field names or class attributes
    return await EmailTemplate.find_all().project("_id", "name", "subject").to_list()

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get a specific template by ID."""
    template = await EmailTemplate.find_one(EmailTemplate.id == template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.post("", response_model=TemplateResponse)
async def create_template(
    template_in: TemplateCreate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new email template."""
    template = EmailTemplate(
        id=uuid4(),
        name=template_in.name,
        subject=template_in.subject,
        html_body=template_in.html_body
    )
    await template.insert()
    return template

@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    template_in: TemplateUpdate,
    user_id: UUID = Depends(get_current_user_id)
):
    """Update an existing template."""
    template = await EmailTemplate.find_one(EmailTemplate.id == template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = template_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    await template.save()
    return template

@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete a template."""
    template = await EmailTemplate.find_one(EmailTemplate.id == template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await template.delete()
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
