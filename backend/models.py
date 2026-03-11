import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from beanie import Document
import pymongo

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class LeadSourceEnum(str, enum.Enum):
    marketing = "Marketing"
    referral = "Referral"
    cold_outreach = "Cold Outreach"
    inbound = "Inbound"
    website_form = "Website Form"
    organic_search = "Organic Search"
    social_media = "Social Media"
    other = "Other"

class LeadStatusEnum(str, enum.Enum):
    hot = "hot"
    warm = "warm"
    cold = "cold"
    new = "new"
    unsubscribed = "unsubscribed"

class EventTypeEnum(str, enum.Enum):
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    COMPLAINT = "complaint"

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    SALES_LEAD = "sales_lead"
    TEAM_MEMBER = "team_member"

class User(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    email: str
    hashed_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    role: UserRole = Field(default=UserRole.TEAM_MEMBER) # Added single role for clarity in CRM
    roles: List[str] = Field(default_factory=list) # Kept for backward compatibility
    manager_id: Optional[uuid.UUID] = None # For hierarchy (Team Member -> Sales Lead)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "users"
        indexes = [
            pymongo.IndexModel([("email", pymongo.ASCENDING)], unique=True)
        ]

class UserAttribute(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    user_id: uuid.UUID
    data: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "user_attributes"
        indexes = [
            pymongo.IndexModel([("user_id", pymongo.ASCENDING)], unique=True)
        ]

class Campaign(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    name: str
    description: Optional[str] = None
    is_active: bool = False
    retry_config: dict = Field(default_factory=lambda: {
        "enabled": True, "first_retry_hours": 48,
        "second_retry_hours": 72, "third_retry_hours": 120
    })
    warmup_config: dict = Field(default_factory=lambda: {
        "enabled": True, "start_limit": 10,
        "daily_increment": 5, "max_volume": 1000,
        "current_limit": 10
    })
    warmup_last_limit_increase: Optional[datetime] = None
    owner_id: uuid.UUID
    contact_list_id: Optional[uuid.UUID] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "campaigns"
        indexes = [
            "name",
            "owner_id",
            pymongo.IndexModel([("owner_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        ]

class Workflow(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    name: str
    description: Optional[str] = None
    campaign_id: Optional[uuid.UUID] = None
    is_active: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "workflows"
        indexes = [
            pymongo.IndexModel([("name", pymongo.ASCENDING)], unique=True),
            "campaign_id",
            pymongo.IndexModel([("campaign_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        ]

class WorkflowNode(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    workflow_id: uuid.UUID
    type: str
    config: dict
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "workflow_nodes"
        indexes = [
            "workflow_id"
        ]

class WorkflowEdge(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    workflow_id: uuid.UUID
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    condition: Optional[dict] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "workflow_edges"
        indexes = [
            "workflow_id", "from_node_id", "to_node_id"
        ]

class EmailTemplate(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    name: str
    subject: str
    html_body: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "email_templates"
        indexes = [
            pymongo.IndexModel([("name", pymongo.ASCENDING)], unique=True)
        ]

class EmailSend(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    template_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    campaign_id: Optional[uuid.UUID] = None
    workflow_id: Optional[uuid.UUID] = None
    workflow_step_id: Optional[uuid.UUID] = None
    to_email: str
    status: str = "queued"
    provider_message_id: Optional[str] = None
    unsubscribe_token: uuid.UUID = Field(default_factory=uuid.uuid4)
    variant_id: Optional[uuid.UUID] = None
    variant_letter: Optional[str] = None
    data: Optional[dict] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "email_sends"
        indexes = [
            "status",
            "created_at",
            "user_id", "campaign_id",
            pymongo.IndexModel([("campaign_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]),
            pymongo.IndexModel([("unsubscribe_token", pymongo.ASCENDING)], unique=True)
        ]

class Event(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    type: str
    user_id: uuid.UUID
    campaign_id: Optional[uuid.UUID] = None
    workflow_id: Optional[uuid.UUID] = None
    workflow_step_id: Optional[uuid.UUID] = None
    email_send_id: Optional[uuid.UUID] = None
    data: Optional[dict] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "events"
        indexes = [
            "type",
            "created_at",
            "user_id", "campaign_id", "email_send_id"
        ]

class LeadScore(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    user_id: uuid.UUID
    score: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "lead_scores"
        indexes = [
            pymongo.IndexModel([("user_id", pymongo.ASCENDING)], unique=True)
        ]

class Pipeline(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "pipelines"
        indexes = [
            pymongo.IndexModel([("name", pymongo.ASCENDING)], unique=True)
        ]

class PipelineItem(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    pipeline_id: uuid.UUID
    user_id: uuid.UUID
    stage: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "pipeline_items"
        indexes = [
            "pipeline_id", "user_id"
        ]

class WorkflowInstance(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    workflow_id: uuid.UUID
    user_id: uuid.UUID
    status: str = "pending"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "workflow_instances"
        indexes = [
            "status",
            "updated_at",
            "workflow_id", "user_id"
        ]

class WorkflowStep(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    instance_id: uuid.UUID
    node_id: Optional[uuid.UUID] = None
    status: str = "pending"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "workflow_steps"
        indexes = [
            "status",
            "instance_id", "node_id"
        ]

class WorkflowInstanceData(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    instance_id: uuid.UUID
    data: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "workflow_instance_data"
        indexes = [
            pymongo.IndexModel([("instance_id", pymongo.ASCENDING)], unique=True)
        ]

class WorkflowSnapshot(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    instance_id: uuid.UUID
    step_id: uuid.UUID
    node_id: Optional[uuid.UUID] = None
    data_snapshot: dict
    condition_result: dict
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "workflow_snapshots"
        indexes = [
            "instance_id", "step_id"
        ]

class ConditionEvaluationLog(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    instance_id: uuid.UUID
    node_id: uuid.UUID
    evaluation_result: bool
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "condition_evaluation_logs"
        indexes = [
            "instance_id", "node_id"
        ]

class EmailVariant(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    campaign_id: Optional[uuid.UUID] = None
    workflow_step_id: Optional[uuid.UUID] = None
    subject: str
    html_body: str
    weight: float = 0.5
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "email_variants"
        indexes = [
            "campaign_id",
            pymongo.IndexModel([("campaign_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        ]

class EmailSendingQueue(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    campaign_id: uuid.UUID
    user_id: uuid.UUID
    template_id: uuid.UUID
    status: str = "pending"
    priority: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "email_sending_queue"
        indexes = [
            "status",
            "campaign_id", "user_id", "template_id"
        ]

class UserNote(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    user_id: uuid.UUID
    content: str
    created_by_id: uuid.UUID
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "user_notes"
        indexes = [
            "user_id"
        ]

class Organization(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "organizations"
        indexes = [
            pymongo.IndexModel([("name", pymongo.ASCENDING)], unique=True),
            pymongo.IndexModel([
                ("name", pymongo.TEXT),
                ("industry", pymongo.TEXT)
            ])
        ]

class ContactList(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    name: str
    description: Optional[str] = None
    owner_id: uuid.UUID
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "contact_lists"
        indexes = [
            "name",
            "owner_id",
            pymongo.IndexModel([("owner_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        ]

class Contact(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    contact_list_id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    attributes: dict = Field(default_factory=dict)
    organization_id: Optional[uuid.UUID] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "contacts"
        indexes = [
            "email",
            "contact_list_id",
            pymongo.IndexModel([
                ("first_name", pymongo.TEXT),
                ("last_name", pymongo.TEXT),
                ("email", pymongo.TEXT)
            ])
        ]

class CRMLeadStage(str, enum.Enum):
    LEAD = "lead"
    CALL = "call"
    MEETING = "meeting"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    PROJECT = "project"
    WON = "won"
    LOST = "lost"

class CurrencyCode(str, enum.Enum):
    USD = "USD"
    EGP = "EGP"
    EUR = "EUR"

class Lead(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    contact_id: Optional[uuid.UUID] = None # Optional now as leads can come directly
    company_name: str = "TBD"
    source: Union[LeadSourceEnum, str] = Field(default=LeadSourceEnum.marketing)
    stage: CRMLeadStage = Field(default=CRMLeadStage.LEAD)
    
    # Assignment
    assigned_to_id: Optional[uuid.UUID] = None
    assigned_by_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None

    # Lead Pool / Claim
    is_claimable: bool = False
    claimed_by_id: Optional[uuid.UUID] = None
    
    # Metadata
    proposal_deadline: Optional[datetime] = None
    deal_value: float = 0.0
    deal_currency: CurrencyCode = Field(default=CurrencyCode.USD)
    last_activity_at: datetime = Field(default_factory=utcnow)
    
    # Existing fields for marketing health (keeping compatibility)
    lead_status: LeadStatusEnum = LeadStatusEnum.new
    lead_score: int = 0
    claimed_at: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    last_email_opened_at: Optional[datetime] = None
    last_link_clicked_at: Optional[datetime] = None
    
    # Assignment (Phase 6)
    assigned_at: Optional[datetime] = None
    assignment_type: Optional[str] = None # manual, auto, creator (Phase 6)
    proposal_deadline: Optional[datetime] = None # For deadline alerts (Phase 6)
    deadline_reminder_sent: bool = False # Track if alert was sent (Phase 6)
    
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "leads"
        indexes = [
            # single-field indexes for common filters
            "stage",
            "assigned_to_id",
            "company_name",
            "is_claimable",
            "claimed_by_id",
            "created_at",
            "last_activity_at",
            # text index on company_name for regex/search operations
            pymongo.IndexModel([("company_name", pymongo.TEXT)]),
            # compound index to support the dashboard and list queries that
            # filter by assignee and stage while sorting by lead_score.
            # put lead_score DESC because higher-score leads are often fetched first.
            pymongo.IndexModel(
                [("assigned_to_id", pymongo.ASCENDING),
                 ("stage", pymongo.ASCENDING),
                 ("lead_score", pymongo.DESCENDING)]
            ),
        ]

class EmailRetryAttempt(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    event_id: uuid.UUID
    attempt_number: int
    scheduled_for: datetime
    status: str = "pending"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "email_retry_attempts"
        indexes = [
            "event_id"
        ]

class Setting(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    key: str
    value: dict
    category: Optional[str] = None
    description: Optional[str] = None
    is_encrypted: bool = False
    updated_by_id: Optional[uuid.UUID] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "settings"
        indexes = [
            pymongo.IndexModel([("key", pymongo.ASCENDING)], unique=True),
            "category"
        ]

class Role(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    name: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "roles"
        indexes = [
            pymongo.IndexModel([("name", pymongo.ASCENDING)], unique=True)
        ]

class LeadNote(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    lead_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    content: str
    is_system: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "lead_notes"
        indexes = [
            "lead_id",
            pymongo.IndexModel([("lead_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        ]

class ActivityType(str, enum.Enum):
    CALL = "call"
    MEETING = "meeting"
    NOTE = "note"
    EMAIL = "email"
    SYSTEM = "system"
    PROPOSAL = "proposal"
    REPLY = "reply"
    FORM = "form"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CRMActivity(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    lead_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    type: ActivityType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    meeting_reminder_sent: bool = False # Automation flag
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "crm_activities"
        indexes = [
            "lead_id",
            "user_id",
            "type",
            pymongo.IndexModel([("lead_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        ]

class CRMTask(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    lead_id: uuid.UUID
    assigned_to_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "crm_tasks"
        indexes = [
            "lead_id",
            "assigned_to_id",
            "status",
            "due_date",
            # compound query for user overdue tasks
            pymongo.IndexModel(
                [("assigned_to_id", pymongo.ASCENDING),
                 ("status", pymongo.ASCENDING),
                 ("due_date", pymongo.ASCENDING)]
            )
        ]

class CRMTarget(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    month: str  # Format "YYYY-MM"
    user_id: Optional[uuid.UUID] = None  # None for overall team target
    revenue_target: float = 0.0
    calls_target: int = 0
    proposals_target: int = 0
    meetings_target: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "crm_targets"
        indexes = [
            "month",
            "user_id"
        ]

class CRMNotification(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    user_id: uuid.UUID
    title: str
    message: str
    type: str = "info" # "info", "warning", "success", "error"
    link: Optional[str] = None
    is_read: bool = False
    scheduled_at: Optional[datetime] = None # Future reminders
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "crm_notifications"
        indexes = [
            "user_id",
            "is_read",
            "created_at"
        ]

class OAuthToken(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    user_id: uuid.UUID
    provider: str  # e.g., "google"
    token_data: dict  # Full JSON response from OAuth provider
    scopes: List[str]
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "oauth_tokens"
        indexes = [
            "user_id",
            "provider"
        ]

class GlobalMetrics(Document):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    user_id: Optional[uuid.UUID] = None
    type: str = "dashboard"
    data: dict
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "global_metrics"
        indexes = [
            "user_id",
            "type",
            "updated_at"
        ]

class LeadScoreLog(Document):
    """Tracks individual scoring events that contributed to a lead's score."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    lead_id: uuid.UUID
    event_type: str  # e.g. 'email_opened', 'email_replied', 'meeting_booked'
    points: int
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "lead_score_logs"
        indexes = ["lead_id", "event_type", "created_at"]

class CRMKanbanOrder(Document):
    """Per-user persisted ordering of CRM Kanban columns (stages)."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    user_id: uuid.UUID
    stage_order: List[str] = Field(default_factory=list)  # e.g. ["lead","call",...]
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "crm_kanban_order"
        indexes = [
            pymongo.IndexModel([("user_id", pymongo.ASCENDING)], unique=True)
        ]

class CRMInboundEmail(Document):
    """Stores parsed inbound emails for auditing and potential lead creation."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")
    from_email: str
    subject: str
    body: str
    lead_id: Optional[uuid.UUID] = None
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "crm_inbound_emails"
        indexes = ["from_email", "lead_id", "created_at"]


__beanie_models__ = [
    User, UserAttribute, Campaign, Workflow, WorkflowNode, WorkflowEdge,
    EmailTemplate, EmailSend, Event, LeadScore, Pipeline, PipelineItem,
    WorkflowInstance, WorkflowStep, WorkflowInstanceData, WorkflowSnapshot,
    ConditionEvaluationLog, EmailVariant, EmailSendingQueue, UserNote,
    ContactList, Contact, Lead, EmailRetryAttempt, Setting, Role, LeadNote,
    CRMActivity, CRMTask, CRMTarget, CRMNotification, OAuthToken,
    GlobalMetrics, Organization, LeadScoreLog, CRMKanbanOrder, CRMInboundEmail
]
