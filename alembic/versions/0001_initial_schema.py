"""initial marketing automation schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-03 00:00:00
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users & Roles ###########################################################

    op.create_table(
        "users",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100)),
        sa.Column("last_name", sa.String(length=100)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "roles",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    op.create_table(
        "user_attributes",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "data",
            psql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_attributes_user_id"),
    )

    # Campaigns & Workflows ###################################################

    op.create_table(
        "campaigns",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_campaigns_name"),
    )

    op.create_table(
        "workflows",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("campaign_id", psql.UUID(as_uuid=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("name", name="uq_workflows_name"),
    )

    op.create_table(
        "workflow_nodes",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column(
            "config",
            psql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_workflow_nodes_workflow_id", "workflow_nodes", ["workflow_id"])

    op.create_table(
        "workflow_edges",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_node_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_node_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("condition", psql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_node_id"], ["workflow_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_node_id"], ["workflow_nodes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_workflow_edges_workflow_id", "workflow_edges", ["workflow_id"])

    # Workflow runtime ########################################################

    op.create_table(
        "workflow_instances",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_workflow_instances_workflow_id", "workflow_instances", ["workflow_id"])
    op.create_index("ix_workflow_instances_user_id", "workflow_instances", ["user_id"])

    op.create_table(
        "workflow_steps",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instance_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", psql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["instance_id"], ["workflow_instances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["workflow_nodes.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_workflow_steps_instance_id", "workflow_steps", ["instance_id"])

    # Email system ############################################################

    op.create_table(
        "email_templates",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_email_templates_name"),
    )

    op.create_table(
        "email_sends",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", psql.UUID(as_uuid=True)),
        sa.Column("user_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", psql.UUID(as_uuid=True)),
        sa.Column("workflow_id", psql.UUID(as_uuid=True)),
        sa.Column("workflow_step_id", psql.UUID(as_uuid=True)),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("provider_message_id", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["template_id"], ["email_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_step_id"], ["workflow_steps.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_email_sends_user_id", "email_sends", ["user_id"])
    op.create_index("ix_email_sends_campaign_id", "email_sends", ["campaign_id"])

    # Events ##################################################################

    op.create_table(
        "events",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("user_id", psql.UUID(as_uuid=True)),
        sa.Column("campaign_id", psql.UUID(as_uuid=True)),
        sa.Column("workflow_id", psql.UUID(as_uuid=True)),
        sa.Column("workflow_step_id", psql.UUID(as_uuid=True)),
        sa.Column("email_send_id", psql.UUID(as_uuid=True)),
        sa.Column("metadata", psql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_step_id"], ["workflow_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["email_send_id"], ["email_sends.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_events_type_created_at", "events", ["type", "created_at"])
    op.create_index("ix_events_user_id", "events", ["user_id"])

    # Segments & Lead scoring #################################################

    op.create_table(
        "segments",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("query", psql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_segments_name"),
    )

    op.create_table(
        "lead_scores",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_lead_scores_user_id"),
    )

    op.create_table(
        "lead_score_rules",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("conditions", psql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_lead_score_rules_name"),
    )

    # Pipelines (CRM lite) ####################################################

    op.create_table(
        "pipelines",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_pipelines_name"),
    )

    op.create_table(
        "pipeline_items",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pipeline_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", psql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_pipeline_items_pipeline_id", "pipeline_items", ["pipeline_id"])
    op.create_index("ix_pipeline_items_user_id", "pipeline_items", ["user_id"])

    # A/B testing #############################################################

    op.create_table(
        "ab_tests",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("name", name="uq_ab_tests_name"),
    )

    op.create_table(
        "ab_variants",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ab_test_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("config", psql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("traffic_percentage", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["ab_test_id"], ["ab_tests.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ab_test_id", "name", name="uq_ab_variants_ab_test_name"),
    )

    # Suppression & Audit #####################################################

    op.create_table(
        "suppression_list",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("email", name="uq_suppression_list_email"),
    )
    op.create_index("ix_suppression_list_email", "suppression_list", ["email"])

    op.create_table(
        "audit_logs",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", psql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", psql.UUID(as_uuid=True)),
        sa.Column("metadata", psql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_suppression_list_email", table_name="suppression_list")
    op.drop_table("suppression_list")

    op.drop_table("ab_variants")
    op.drop_table("ab_tests")

    op.drop_index("ix_pipeline_items_user_id", table_name="pipeline_items")
    op.drop_index("ix_pipeline_items_pipeline_id", table_name="pipeline_items")
    op.drop_table("pipeline_items")
    op.drop_table("pipelines")

    op.drop_table("lead_score_rules")
    op.drop_table("lead_scores")
    op.drop_table("segments")

    op.drop_index("ix_events_user_id", table_name="events")
    op.drop_index("ix_events_type_created_at", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_email_sends_campaign_id", table_name="email_sends")
    op.drop_index("ix_email_sends_user_id", table_name="email_sends")
    op.drop_table("email_sends")
    op.drop_table("email_templates")

    op.drop_index("ix_workflow_steps_instance_id", table_name="workflow_steps")
    op.drop_table("workflow_steps")

    op.drop_index("ix_workflow_instances_user_id", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_workflow_id", table_name="workflow_instances")
    op.drop_table("workflow_instances")

    op.drop_index("ix_workflow_edges_workflow_id", table_name="workflow_edges")
    op.drop_table("workflow_edges")

    op.drop_index("ix_workflow_nodes_workflow_id", table_name="workflow_nodes")
    op.drop_table("workflow_nodes")

    op.drop_table("workflows")

    op.drop_table("campaigns")

    op.drop_table("user_attributes")
    op.drop_table("user_roles")
    op.drop_table("roles")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")