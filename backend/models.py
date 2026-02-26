import uuid
import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Integer,
    Text,
    UniqueConstraint,
    Enum as SaEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import sqlalchemy as sa

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class LeadStatusEnum(str, enum.Enum):
    hot = "hot"           # Clicked link
    warm = "warm"         # Opened email but didn't click
    cold = "cold"         # Ignored all emails (3 attempts)
    new = "new"           # Just added, no emails sent yet
    unsubscribed = "unsubscribed"


class EventTypeEnum(str, enum.Enum):
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    COMPLAINT = "complaint"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    attributes: Mapped["UserAttribute"] = relationship(
        "UserAttribute", uselist=False, back_populates="user", cascade="all, delete-orphan"
    )
    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    assigned_leads: Mapped[list["Lead"]] = relationship(
        "Lead", foreign_keys="Lead.assigned_to_id", back_populates="assigned_to"
    )

class UserAttribute(Base, TimestampMixin):
    __tablename__ = "user_attributes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    data: Mapped[dict] = mapped_column(JSONB, default=dict)

    user: Mapped[User] = relationship("User", back_populates="attributes")

class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    
    retry_config: Mapped[dict] = mapped_column(
        JSONB, 
        default=lambda: {
            "enabled": True,
            "first_retry_hours": 48,
            "second_retry_hours": 72,
            "third_retry_hours": 120
        }
    )
    warmup_config: Mapped[dict] = mapped_column(
        JSONB, 
        default=lambda: {
            "enabled": True,
            "start_limit": 10,
            "daily_increment": 5,
            "max_volume": 1000,
            "current_limit": 10
        }
    )
    warmup_last_limit_increase: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    contact_list_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contact_lists.id", ondelete="SET NULL"), nullable=True
    )
    
    owner: Mapped["User"] = relationship("User")
    contact_list: Mapped[Optional["ContactList"]] = relationship("ContactList")
    workflow: Mapped[Optional["Workflow"]] = relationship("Workflow", back_populates="campaign", uselist=False)

class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    campaign: Mapped[Optional[Campaign]] = relationship("Campaign", back_populates="workflow")
    nodes: Mapped[list["WorkflowNode"]] = relationship(
        "WorkflowNode", back_populates="workflow", cascade="all, delete-orphan"
    )

class WorkflowNode(Base, TimestampMixin):
    __tablename__ = "workflow_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(50)) # start, email, delay, condition, end
    config: Mapped[dict] = mapped_column(JSONB)

    workflow: Mapped[Workflow] = relationship("Workflow", back_populates="nodes")
    outgoing_edges: Mapped[list["WorkflowEdge"]] = relationship(
        "WorkflowEdge", foreign_keys="WorkflowEdge.from_node_id", back_populates="from_node"
    )
    incoming_edges: Mapped[list["WorkflowEdge"]] = relationship(
        "WorkflowEdge", foreign_keys="WorkflowEdge.to_node_id", back_populates="to_node"
    )

class WorkflowEdge(Base, TimestampMixin):
    __tablename__ = "workflow_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE")
    )
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE")
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE")
    )
    condition: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    from_node: Mapped[WorkflowNode] = relationship(
        "WorkflowNode", foreign_keys=[from_node_id], back_populates="outgoing_edges"
    )
    to_node: Mapped[WorkflowNode] = relationship(
        "WorkflowNode", foreign_keys=[to_node_id], back_populates="incoming_edges"
    )

    __table_args__ = (
        UniqueConstraint("from_node_id", "to_node_id", name="uq_workflow_edge_path"),
    )

class EmailTemplate(Base, TimestampMixin):
    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True)
    subject: Mapped[str] = mapped_column(String(255))
    html_body: Mapped[str] = mapped_column(Text)

class EmailSend(Base, TimestampMixin):
    __tablename__ = "email_sends"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    workflow_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_steps.id", ondelete="SET NULL"), nullable=True
    )
    to_email: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="queued")
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unsubscribe_token: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, default=uuid.uuid4
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_variants.id", ondelete="SET NULL"), nullable=True
    )
    variant_letter: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    template: Mapped[Optional[EmailTemplate]] = relationship("EmailTemplate")
    user: Mapped[User] = relationship("User")
    campaign: Mapped[Optional[Campaign]] = relationship("Campaign")
    workflow: Mapped[Optional[Workflow]] = relationship("Workflow")

    __table_args__ = (
        Index("ix_email_sends_status_created", "status", sa.literal_column("created_at DESC")),
        Index("ix_email_sends_campaign_status", "campaign_id", "status"),
    )

class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(String(50), index=True) # sent, opened, clicked, bounced
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    workflow_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_steps.id", ondelete="SET NULL"), nullable=True
    )
    email_send_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_sends.id", ondelete="SET NULL"), nullable=True
    )
    data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    user: Mapped[User] = relationship("User")
    email_send: Mapped[Optional["EmailSend"]] = relationship("EmailSend")

    __table_args__ = (
        Index("ix_events_campaign_type_created", "campaign_id", "type", sa.literal_column("created_at DESC")),
        Index("ix_events_user_type_created", "user_id", "type", sa.literal_column("created_at DESC")),
        Index("ix_events_email_send_type", "email_send_id", "type"),
        Index("ix_events_created_at", sa.literal_column("created_at DESC")),
    )

class LeadScore(Base, TimestampMixin):
    __tablename__ = "lead_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    score: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship("User")

class Pipeline(Base, TimestampMixin):
    __tablename__ = "pipelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class PipelineItem(Base, TimestampMixin):
    __tablename__ = "pipeline_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    stage: Mapped[str] = mapped_column(String(50)) # lead, prospect, qualified, closed
    
    user: Mapped[User] = relationship("User")

class WorkflowInstance(Base, TimestampMixin):
    __tablename__ = "workflow_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")

    workflow: Mapped[Workflow] = relationship("Workflow")
    user: Mapped[User] = relationship("User")

    __table_args__ = (
        Index("ix_workflow_instances_status_updated", "status", sa.literal_column("updated_at DESC")),
        Index("ix_workflow_instances_workflow_status", "workflow_id", "status"),
    )

class WorkflowStep(Base, TimestampMixin):
    __tablename__ = "workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_instances.id", ondelete="CASCADE")
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_workflow_steps_instance_status", "instance_id", "status"),
        Index("ix_workflow_steps_node_status", "node_id", "status"),
    )

class WorkflowInstanceData(Base, TimestampMixin):
    __tablename__ = "workflow_instance_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_instances.id", ondelete="CASCADE"), unique=True
    )
    data: Mapped[dict] = mapped_column(JSONB, default=dict)

class WorkflowSnapshot(Base, TimestampMixin):
    __tablename__ = "workflow_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_instances.id", ondelete="CASCADE"), index=True
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_steps.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=True
    )
    data_snapshot: Mapped[dict] = mapped_column(JSONB)
    condition_result: Mapped[dict] = mapped_column(JSONB)

class ConditionEvaluationLog(Base, TimestampMixin):
    __tablename__ = "condition_evaluation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_instances.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_nodes.id", ondelete="CASCADE"), index=True
    )
    evaluation_result: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class EmailVariant(Base, TimestampMixin):
    __tablename__ = "email_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True
    )
    workflow_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(255))
    html_body: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(sa.Float, default=0.5)

class EmailSendingQueue(Base, TimestampMixin):
    __tablename__ = "email_sending_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=0)

class UserNote(Base, TimestampMixin):
    __tablename__ = "user_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

class ContactList(Base, TimestampMixin):
    __tablename__ = "contact_lists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Relationships
    contacts: Mapped[list["Contact"]] = relationship("Contact", back_populates="contact_list", cascade="all, delete-orphan")

class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contact_lists.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    contact_list: Mapped["ContactList"] = relationship("ContactList", back_populates="contacts")
    lead: Mapped[Optional["Lead"]] = relationship("Lead", back_populates="contact", uselist=False)

    __table_args__ = (
        Index("ix_contacts_list_email", "contact_list_id", "email"),
    )

class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), unique=True, index=True
    )
    
    # Lead-specific fields
    lead_status: Mapped[LeadStatusEnum] = mapped_column(
        SaEnum(LeadStatusEnum, name="leadstatusenum", create_type=False), 
        default=LeadStatusEnum.new, 
        index=True
    )
    lead_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Assignment & ownership
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Engagement tracking
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_email_opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_link_clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    contact: Mapped["Contact"] = relationship("Contact", back_populates="lead")
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_to_id], back_populates="assigned_leads"
    )
    notes: Mapped[list["LeadNote"]] = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_leads_status_score", "lead_status", sa.literal_column("lead_score DESC")),
        Index("ix_leads_assigned_to", "assigned_to_id", postgresql_where=sa.literal_column("assigned_to_id IS NOT NULL")),
    )

class EmailRetryAttempt(Base, TimestampMixin):
    __tablename__ = "email_retry_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE")
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="pending")

class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[dict] = mapped_column(JSONB)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), unique=True)

class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE")
    )

    user: Mapped[User] = relationship("User", back_populates="roles")
    role: Mapped[Role] = relationship("Role")

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


class LeadNote(Base, TimestampMixin):
    __tablename__ = "lead_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="notes")
    user: Mapped[Optional["User"]] = relationship("User")
