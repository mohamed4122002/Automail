from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import List, Optional
from ..models import Campaign, Workflow
from ..schemas.campaigns import CampaignOut, CampaignCreate, CampaignList, CampaignDetail
from ..schemas.campaign_analytics import (
    AnalyticsResponse,
    RecipientsResponse,
    RecipientDetail,
    WorkflowVisualization,
    TestEmailRequest,
    DuplicateCampaignRequest,
    BulkActionRequest,
    ExportRecipientsRequest
)
from ..services.campaigns import CampaignService
from ..services.campaign_manager import CampaignManagerService
from ..services.campaign_analytics import CampaignAnalyticsService
from .deps import get_current_user_id
import logging

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.get("", response_model=List[CampaignList])
async def list_campaigns(
    user_id: UUID = Depends(get_current_user_id)
) -> List[CampaignList]:
    service = CampaignService()
    return await service.list_campaigns(user_id)


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(
    payload: CampaignCreate,
    user_id: UUID = Depends(get_current_user_id)
) -> Campaign:
    campaign = Campaign(
        name=payload.name,
        description=payload.description,
        owner_id=user_id,
        contact_list_id=payload.contact_list_id
    )
    await campaign.insert()
    
    return campaign


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    service = CampaignService()
    try:
        return await service.get_campaign_detail(campaign_id, owner_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: UUID,
    payload: dict, # Using dict for partial updates
    user_id: UUID = Depends(get_current_user_id)
) -> Campaign:
    campaign = await Campaign.find_one(
        Campaign.id == campaign_id,
        Campaign.owner_id == user_id
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    for key, value in payload.items():
        if hasattr(campaign, key):
            # Special handling for UUID strings
            if key == "contact_list_id" and isinstance(value, str):
                value = UUID(value)
            setattr(campaign, key, value)
            
    await campaign.save()
    
    # Broadcast configuration update
    from .realtime import broadcast_event
    from datetime import datetime
    
    details = []
    if "name" in payload: details.append(f"Name changed to '{payload['name']}'")
    if "contact_list_id" in payload: details.append("Targeting list updated")
    if "warmup_config" in payload: details.append("Deliverability parameters adjusted")
    
    await broadcast_event({
        "type": "event",
        "event_type": "campaign_config_updated",
        "campaign_id": str(campaign_id),
        "campaign_name": campaign.name,
        "detail": "; ".join(details) if details else "Configuration updated",
        "timestamp": datetime.utcnow().isoformat()
    })

    return campaign


@router.post("/{campaign_id}/activate")
async def activate_campaign(
    campaign_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Activate a campaign and start workflow instances for all contacts.
    Returns detailed status including worker availability.
    """
    manager = CampaignManagerService()
    try:
        result = await manager.activate_campaign(campaign_id, user_id)
        
        # Check worker status
        from ..celery_app import celery_app
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            worker_available = bool(stats and len(stats) > 0)
        except:
            worker_available = False
        
        # Enhance response with worker status
        result["worker_status"] = {
            "available": worker_available,
            "warning": None if worker_available else "No Celery workers detected. Tasks will queue but not execute until workers are started."
        }
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Campaign activation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Campaign activation failed: {str(e)}")


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    manager = CampaignManagerService()
    try:
        return await manager.pause_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{campaign_id}/workflow")
async def update_campaign_workflow(
    campaign_id: UUID,
    workflow_id: UUID = Query(..., alias="workflow_id"),
    user_id: UUID = Depends(get_current_user_id)
):
    manager = CampaignManagerService()
    try:
        return await manager.update_workflow(campaign_id, workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{campaign_id}/warmup-status")
async def get_campaign_warmup_status(
    campaign_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    campaign = await Campaign.find_one(
        Campaign.id == campaign_id,
        Campaign.owner_id == user_id
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Calculate real status
    # This matches the frontend expectations in CampaignDetail.tsx
    from ..models import EmailSend
    from datetime import datetime, timezone
    
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    sent_today = await EmailSend.find(
        EmailSend.campaign_id == campaign_id,
        EmailSend.created_at >= start_of_day
    ).count()
    
    cfg = campaign.warmup_config or {}
    current_limit = cfg.get("current_limit", 10)
    
    return {
        "enabled": cfg.get("enabled", False),
        "current_limit": current_limit,
        "sent_today": sent_today,
        "max_volume": cfg.get("max_volume", 1000),
        "progress_pct": min(100, int((sent_today / current_limit) * 100)) if current_limit > 0 else 0
    }


# ============================================================================
# NEW ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/{campaign_id}/analytics", response_model=AnalyticsResponse)
async def get_campaign_analytics(
    campaign_id: UUID,
    days: int = 30,  # Number of days for time series data
    user_id: UUID = Depends(get_current_user_id)
):
    """Get comprehensive analytics data for a campaign."""
    analytics_service = CampaignAnalyticsService()
    try:
        return await analytics_service.get_analytics(campaign_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{campaign_id}/recipients", response_model=RecipientsResponse)
async def get_campaign_recipients(
    campaign_id: UUID,
    page: int = 1,
    page_size: int = 50,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,  # Search by email
    sort_by: Optional[str] = Query("created_at", description="Field to sort by (created_at, email, name)"),
    order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get paginated list of campaign recipients with their status."""
    analytics_service = CampaignAnalyticsService()
    try:
        return await analytics_service.get_recipients(
            campaign_id=campaign_id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            search=search,
            sort_by=sort_by,
            order=order
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{campaign_id}/recipients/{recipient_id}", response_model=RecipientDetail)
async def get_recipient_detail(
    campaign_id: UUID,
    recipient_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get detailed information about a specific recipient."""
    analytics_service = CampaignAnalyticsService()
    try:
        return await analytics_service.get_recipient_detail(campaign_id, recipient_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{campaign_id}/workflow", response_model=WorkflowVisualization)
async def get_campaign_workflow(
    campaign_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """Get workflow visualization data with execution statistics."""
    analytics_service = CampaignAnalyticsService()
    try:
        return await analytics_service.get_workflow_visualization(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{campaign_id}/recipients/bulk")
async def bulk_recipients_action(
    campaign_id: UUID,
    payload: BulkActionRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Perform bulk actions on recipients (tag, untag, remove)."""
    analytics_service = CampaignAnalyticsService()
    try:
        return await analytics_service.bulk_recipients_action(
            campaign_id=campaign_id,
            action=payload.action,
            recipient_ids=payload.recipient_ids,
            data=payload.action_data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{campaign_id}/recipients/export")
async def export_recipients_csv(
    campaign_id: UUID,
    payload: ExportRecipientsRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Export selected recipients to CSV."""
    from fastapi.responses import StreamingResponse
    import io
    
    analytics_service = CampaignAnalyticsService()
    try:
        csv_content = await analytics_service.export_recipients(
            campaign_id=campaign_id,
            status_filter=payload.status_filter,
            search=payload.search,
            recipient_ids=payload.recipient_ids,
            format=payload.format
        )
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=campaign_{campaign_id}_recipients.csv"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# QUICK ACTIONS ENDPOINTS
# ============================================================================

@router.post("/{campaign_id}/test-email")
async def send_test_email(
    campaign_id: UUID,
    payload: TestEmailRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Send test email to specified recipients."""
    analytics_service = CampaignAnalyticsService()
    try:
        return await analytics_service.send_test_email(
            campaign_id=campaign_id,
            recipient_emails=payload.recipient_emails,
            template_id=payload.template_id,
            use_campaign_workflow=payload.use_campaign_workflow
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{campaign_id}/duplicate")
async def duplicate_campaign(
    campaign_id: UUID,
    payload: DuplicateCampaignRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """Duplicate an existing campaign."""
    analytics_service = CampaignAnalyticsService()
    try:
        return await analytics_service.duplicate_campaign(
            campaign_id=campaign_id,
            new_name=payload.new_name,
            copy_workflow=payload.copy_workflow,
            copy_contacts=payload.copy_contacts,
            owner_id=user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{campaign_id}/export")
async def export_campaign_data(
    campaign_id: UUID,
    format: str = "csv",
    include_recipients: bool = True,
    include_analytics: bool = True,
    include_events: bool = False,
    user_id: UUID = Depends(get_current_user_id)
):
    """Export campaign data in various formats."""
    from fastapi.responses import StreamingResponse
    from datetime import datetime
    import io
    
    analytics_service = CampaignAnalyticsService()
    try:
        data = await analytics_service.export_campaign_data(
            campaign_id=campaign_id,
            format=format,
            include_recipients=include_recipients,
            include_analytics=include_analytics,
            include_events=include_events
        )
        
        # Return as downloadable file
        filename = f"campaign_{campaign_id}_{datetime.now().strftime('%Y%m%d')}.{format}"
        
        if format == "csv":
            return StreamingResponse(
                io.StringIO(data),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        elif format == "json":
            return StreamingResponse(
                io.StringIO(data),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

