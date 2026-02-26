from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List

# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class CampaignAnalytics(BaseModel):
    """Comprehensive analytics data for campaign overview."""
    
    # Core metrics
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    unsubscribed: int = 0
    replied: int = 0
    converted: int = 0
    
    # Calculated rates
    delivery_rate: float = 0.0  # (delivered / sent) * 100
    open_rate: float = 0.0      # (opened / delivered) * 100
    click_rate: float = 0.0     # (clicked / delivered) * 100
    bounce_rate: float = 0.0    # (bounced / sent) * 100
    conversion_rate: float = 0.0 # (converted / delivered) * 100
    
    # Trend data (compared to previous period)
    sent_trend: Optional[float] = None  # % change
    opened_trend: Optional[float] = None
    clicked_trend: Optional[float] = None
    
    class Config:
        from_attributes = True


class TimeSeriesDataPoint(BaseModel):
    """Single data point for time series charts."""
    date: str  # ISO format date
    sent: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0


class HeatmapDataPoint(BaseModel):
    """Engagement heatmap data point."""
    hour: int  # 0-23
    day: str   # Mon, Tue, Wed, etc.
    opens: int = 0
    clicks: int = 0


class AnalyticsResponse(BaseModel):
    """Complete analytics response with all data."""
    metrics: CampaignAnalytics
    time_series: List[TimeSeriesDataPoint] = []
    heatmap: List[HeatmapDataPoint] = []
    
    # Top performing data
    top_links: List[dict] = []  # [{url, clicks, unique_clicks}]
    top_subjects: List[dict] = []  # [{subject, opens, open_rate}]


# ============================================================================
# RECIPIENTS SCHEMAS
# ============================================================================

class RecipientStatus(BaseModel):
    """Detailed recipient status information."""
    user_id: UUID
    email: str
    name: Optional[str] = None
    status: str  # sent, opened, clicked, bounced, unsubscribed
    engagement_score: int = 0  # 0-100
    
    # Activity timestamps
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    
    # Workflow progress
    current_workflow_node: Optional[str] = None
    workflow_node_id: Optional[UUID] = None
    
    # Engagement details
    total_opens: int = 0
    total_clicks: int = 0
    emails_received: int = 0
    
    class Config:
        from_attributes = True


class RecipientDetail(RecipientStatus):
    """Extended recipient details with full history."""
    user_id: UUID
    
    # Event timeline
    events: List[dict] = []  # [{type, timestamp, metadata}]
    
    # Email history
    emails: List[dict] = []  # [{subject, sent_at, status, template_id}]
    
    # Custom attributes
    attributes: dict = {}


class RecipientsResponse(BaseModel):
    """Paginated recipients list response."""
    recipients: List[RecipientStatus]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int
    sort_by: Optional[str] = "created_at"
    order: Optional[str] = "desc"
    
    # Summary stats
    summary: dict = {}  # {sent: X, opened: Y, clicked: Z, etc.}


# ============================================================================
# WORKFLOW SCHEMAS
# ============================================================================

class WorkflowNodeStats(BaseModel):
    """Statistics for a single workflow node."""
    node_id: UUID
    node_type: str
    node_label: str
    
    # Current state
    leads_active: int = 0  # Currently at this node
    leads_completed: int = 0  # Passed through
    leads_failed: int = 0  # Failed at this node
    
    # Performance
    avg_time_at_node: Optional[float] = None  # seconds
    success_rate: float = 0.0  # % that successfully completed
    
    class Config:
        from_attributes = True


class WorkflowVisualization(BaseModel):
    """Workflow structure with execution stats."""
    workflow_id: UUID
    workflow_name: str
    is_active: bool
    
    # Nodes with stats
    nodes: List[dict] = []  # Full node data with positions
    edges: List[dict] = []  # Connections between nodes
    
    # Node statistics
    node_stats: List[WorkflowNodeStats] = []
    
    # Overall workflow stats
    total_instances: int = 0
    active_instances: int = 0
    completed_instances: int = 0
    failed_instances: int = 0
    
    class Config:
        from_attributes = True


# ============================================================================
# QUICK ACTIONS SCHEMAS
# ============================================================================

class TestEmailRequest(BaseModel):
    """Request to send test email."""
    recipient_emails: List[str]
    template_id: Optional[UUID] = None
    use_campaign_workflow: bool = True


class DuplicateCampaignRequest(BaseModel):
    """Request to duplicate a campaign."""
    new_name: str
    copy_workflow: bool = True
    copy_contacts: bool = False


class ExportDataRequest(BaseModel):
    """Request to export campaign data."""
    format: str = "csv"  # csv, json, xlsx
    include_recipients: bool = True
    include_analytics: bool = True
    include_events: bool = False


# ============================================================================
# BULK ACTIONS SCHEMAS
# ============================================================================

class BulkActionRequest(BaseModel):
    """Request for bulk operations on recipients."""
    recipient_ids: List[UUID]  # List of User UUIDs
    action: str  # tag, untag, remove, export
    action_data: Optional[dict] = None  # Additional data (e.g., tags to add/remove)
    
    # For export action
    export_format: Optional[str] = "csv"


class ExportRecipientsRequest(BaseModel):
    """Request to export recipients."""
    status_filter: Optional[str] = None
    search: Optional[str] = None
    recipient_ids: Optional[List[UUID]] = None  # If specific IDs selected
    format: str = "csv"

