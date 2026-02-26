"""add_lead_notes

Revision ID: f0f016a25265
Revises: f07927f9c37b
Create Date: 2026-02-09 10:42:14.391188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0f016a25265'
down_revision: Union[str, None] = 'f07927f9c37b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lead_notes',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('lead_id', sa.UUID(as_uuid=True), sa.ForeignKey('leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_system', sa.Boolean(), default=False, nullable=False)
    )
    op.create_index(op.f('ix_lead_notes_lead_id'), 'lead_notes', ['lead_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lead_notes_lead_id'), table_name='lead_notes')
    op.drop_table('lead_notes')
