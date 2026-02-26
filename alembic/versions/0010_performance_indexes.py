"""Add performance indexes for high-frequency query patterns

Revision ID: 0010_performance_indexes
Revises: 0005_add_contact_list_id
Create Date: 2026-02-18 10:47:00.000000

These indexes target the most expensive query patterns identified in the
DB audit (Feb 2026). All use CONCURRENTLY to avoid table locks on live DB.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0010_performance_indexes'
down_revision = '0005_add_contact_list_id'
branch_labels = None
depends_on = None


# revision identifiers, used by Alembic.
revision = '0010_performance_indexes'
down_revision = '0005_add_contact_list_id'
branch_labels = None
depends_on = None


def upgrade():
    # CONCURRENTLY cannot run inside a transaction block
    with op.get_context().autocommit_block():
        # ── events table ──────────────────────────────────────────────────────────
        # Used by: analytics dashboard (campaign_id + type filter, ordered by date)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_events_campaign_type_created
                ON events (campaign_id, type, created_at DESC)
        """)

        # Used by: retry task (check if email was opened), tracking API
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_events_email_send_type
                ON events (email_send_id, type)
        """)

        # Used by: analytics time-series queries (date_trunc grouping)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_events_created_at
                ON events (created_at DESC)
        """)

        # Used by: workflow condition evaluation (user_id + type lookup)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_events_user_type_created
                ON events (user_id, type, created_at DESC)
        """)

        # ── email_sends table ─────────────────────────────────────────────────────
        # Used by: retry task (full scan for status='sent' + date filter)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_email_sends_status_created
                ON email_sends (status, created_at DESC)
        """)

        # Used by: campaign analytics (campaign_id + status aggregation)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_email_sends_campaign_status
                ON email_sends (campaign_id, status)
        """)

        # ── workflow_instances table ──────────────────────────────────────────────
        # Used by: stale instance cleanup task (status='running' + updated_at filter)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_workflow_instances_status_updated
                ON workflow_instances (status, updated_at)
        """)

        # Used by: campaign monitoring (workflow_id + status aggregation)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_workflow_instances_workflow_status
                ON workflow_instances (workflow_id, status)
        """)

        # ── workflow_steps table ──────────────────────────────────────────────────
        # Used by: workflow advancement (instance_id lookup + status filter)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_workflow_steps_instance_status
                ON workflow_steps (instance_id, status)
        """)

        # Used by: monitoring (node performance avg duration queries)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_workflow_steps_node_status
                ON workflow_steps (node_id, status)
        """)

        # ── contacts table ────────────────────────────────────────────────────────
        # Used by: import duplicate check (contact_list_id + email lookup)
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_contacts_list_email
                ON contacts (contact_list_id, email)
        """)

        # ── leads table ───────────────────────────────────────────────────────────
        # Used by: lead listing with status filter
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_leads_status_score
                ON leads (lead_status, lead_score DESC)
        """)

        # Used by: assigned lead queries
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_leads_assigned_to
                ON leads (assigned_to_id)
            WHERE assigned_to_id IS NOT NULL
        """)


def downgrade():
    indexes = [
        "ix_events_campaign_type_created",
        "ix_events_email_send_type",
        "ix_events_created_at",
        "ix_events_user_type_created",
        "ix_email_sends_status_created",
        "ix_email_sends_campaign_status",
        "ix_workflow_instances_status_updated",
        "ix_workflow_instances_workflow_status",
        "ix_workflow_steps_instance_status",
        "ix_workflow_steps_node_status",
        "ix_contacts_list_email",
        "ix_leads_status_score",
        "ix_leads_assigned_to",
    ]
    for idx in indexes:
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {idx}")
