"""condition evaluation logs

Revision ID: 0002_condition_logs
Revises: 0001_initial_schema
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql


revision = "0002_condition_logs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "condition_evaluation_logs",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instance_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", psql.UUID(as_uuid=True), nullable=False),
        sa.Column("condition", psql.JSONB(), nullable=False),
        sa.Column("result", sa.Boolean(), nullable=False),
        sa.Column("details", psql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["instance_id"], ["workflow_instances.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["node_id"], ["workflow_nodes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )


def downgrade() -> None:
    op.drop_table("condition_evaluation_logs")

