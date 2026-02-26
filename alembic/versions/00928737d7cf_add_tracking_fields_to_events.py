"""add tracking fields to events

Revision ID: 00928737d7cf
Revises: f0f016a25265
Create Date: 2026-02-09 10:55:42.106930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00928737d7cf'
down_revision: Union[str, None] = 'f0f016a25265'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import sqlalchemy.dialects.postgresql as psql

def upgrade() -> None:
    op.add_column('events', sa.Column('workflow_step_id', psql.UUID(as_uuid=True), nullable=True))
    op.add_column('events', sa.Column('email_send_id', psql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_events_workflow_step_id_workflow_steps', 'events', 'workflow_steps', ['workflow_step_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_events_email_send_id_email_sends', 'events', 'email_sends', ['email_send_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_events_email_send_id_email_sends', 'events', type_='foreignkey')
    op.drop_constraint('fk_events_workflow_step_id_workflow_steps', 'events', type_='foreignkey')
    op.drop_column('events', 'email_send_id')
    op.drop_column('events', 'workflow_step_id')
