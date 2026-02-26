from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from ..db import get_db
from ..services.settings import SettingsService
from ..schemas.settings import (
    SettingResponse, 
    SettingUpdate, 
    EmailProviderConfig,
    SystemPreferences,
    WorkflowPreferences
)
from ..api.deps import get_current_user_id

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/", response_model=list[SettingResponse])
async def list_settings(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all settings, optionally filtered by category."""
    service = SettingsService(db)
    
    if category:
        settings = await service.get_settings_by_category(category)
    else:
        settings = await service.get_all_settings()
    
    return settings

@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Get a specific setting by key."""
    service = SettingsService(db)
    setting = await service.get_setting(key)
    
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return setting

@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    update: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update a setting value."""
    service = SettingsService(db)
    
    # Determine if this should be encrypted based on key
    is_encrypted = key in ["email_provider", "api_keys", "smtp_config"]
    
    setting = await service.create_or_update_setting(
        key=key,
        value=update.value,
        is_encrypted=is_encrypted,
        updated_by_id=user_id
    )
    
    return setting

@router.post("/email_provider", response_model=SettingResponse, include_in_schema=False)
@router.post("/email-provider", response_model=SettingResponse)
async def configure_email_provider(
    config: EmailProviderConfig,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Configure email provider settings."""
    service = SettingsService(db)
    
    setting = await service.create_or_update_setting(
        key="email_provider",
        value=config.model_dump(),
        category="email",
        is_encrypted=True,
        description="Email provider configuration",
        updated_by_id=user_id
    )
    
    return setting

@router.post("/system_preferences", response_model=SettingResponse, include_in_schema=False)
@router.post("/system-preferences", response_model=SettingResponse)
async def update_system_preferences(
    prefs: SystemPreferences,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update system preferences."""
    service = SettingsService(db)
    
    setting = await service.create_or_update_setting(
        key="system_preferences",
        value=prefs.model_dump(),
        category="system",
        is_encrypted=False,
        description="System preferences",
        updated_by_id=user_id
    )
    
    return setting

@router.post("/workflow_preferences", response_model=SettingResponse, include_in_schema=False)
@router.post("/workflow-preferences", response_model=SettingResponse)
async def update_workflow_preferences(
    prefs: WorkflowPreferences,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update workflow preferences."""
    service = SettingsService(db)
    
    setting = await service.create_or_update_setting(
        key="workflow_preferences",
        value=prefs.model_dump(),
        category="workflow",
        is_encrypted=False,
        description="Workflow execution preferences",
        updated_by_id=user_id
    )
    
    return setting

@router.delete("/{key}")
async def delete_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Delete a setting."""
    service = SettingsService(db)
    deleted = await service.delete_setting(key)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return {"message": "Setting deleted successfully"}


@router.post("/email-provider/test")
async def test_email_provider(db: AsyncSession = Depends(get_db)):
    """Test the currently currently configured email provider connection."""
    from ..email_providers import get_email_provider
    
    try:
        provider = await get_email_provider(db)
        is_valid = await provider.test_connection()
        
        if is_valid:
            return {"status": "success", "message": "Email provider connection successful"}
        else:
            return {"status": "error", "message": "Email provider connection failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.post("/email-provider/test-config")
async def test_email_config(
    config: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Test email provider configuration before saving.
    Allows testing new configurations without applying them.
    """
    from ..email_providers import test_email_provider_config
    
    try:
        is_valid, message = await test_email_provider_config(config)
        
        if is_valid:
            return {"status": "success", "message": message}
        else:
            return {"status": "error", "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.post("/email-provider/send-test-email")
async def send_test_email(
    test_email: str,
    db: AsyncSession = Depends(get_db)
):
    """Send a test email to verify configuration."""
    from ..email_providers import get_email_provider
    
    try:
        provider = await get_email_provider(db)
        message_id = await provider.send_email(
            to_email=test_email,
            subject="Test Email from Marketing Automation",
            html_body="""
            <html>
                <body>
                    <h1>Test Email</h1>
                    <p>This is a test email from your Marketing Automation system.</p>
                    <p>If you received this, your email provider is configured correctly!</p>
                </body>
            </html>
            """,
            metadata={"test": "true"}
        )
        
        return {
            "status": "success",
            "message": f"Test email sent to {test_email}",
            "message_id": message_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")
