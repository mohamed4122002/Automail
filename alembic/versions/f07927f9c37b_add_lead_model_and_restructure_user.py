"""add_lead_model_and_restructure_user

Revision ID: f07927f9c37b
Revises: 9f82bf26da92
Create Date: 2026-02-09 10:35:26.402084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f07927f9c37b'
down_revision: Union[str, None] = '9f82bf26da92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure leadstatusenum exists without failing if it already does
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leadstatusenum') THEN "
               "CREATE TYPE leadstatusenum AS ENUM ('hot', 'warm', 'cold', 'new', 'unsubscribed'); "
               "END IF; END $$;")
    
    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_status', postgresql.ENUM('hot', 'warm', 'cold', 'new', 'unsubscribed', name='leadstatusenum', create_type=False), nullable=False, server_default='new'),
        sa.Column('lead_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('assigned_to_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
        sa.Column('last_contacted_at', sa.DateTime(), nullable=True),
        sa.Column('last_email_opened_at', sa.DateTime(), nullable=True),
        sa.Column('last_link_clicked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contact_id')
    )
    
    # Create indexes for leads table
    op.create_index(op.f('ix_leads_contact_id'), 'leads', ['contact_id'], unique=True)
    op.create_index(op.f('ix_leads_lead_status'), 'leads', ['lead_status'], unique=False)
    op.create_index(op.f('ix_leads_assigned_to_id'), 'leads', ['assigned_to_id'], unique=False)
    
    # Add index to contacts.contact_list_id for better join performance
    op.create_index(op.f('ix_contacts_contact_list_id'), 'contacts', ['contact_list_id'], unique=False)
    
    # Remove lead-related columns from users table
    # The enum type will remain in the database since it's now used by the leads table
    op.drop_column('users', 'claimed_at')
    op.drop_column('users', 'claimed_by_id')
    op.drop_column('users', 'lead_status')


def downgrade() -> None:
    # Add back lead-related columns to users table
    op.add_column('users', sa.Column('lead_status', postgresql.ENUM('hot', 'warm', 'cold', 'new', 'unsubscribed', name='leadstatusenum', create_type=False), nullable=False, server_default='new'))
    op.add_column('users', sa.Column('claimed_by_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('claimed_at', sa.DateTime(), nullable=True))
    
    # Recreate the foreign key for claimed_by_id
    op.create_foreign_key('users_claimed_by_id_fkey', 'users', 'users', ['claimed_by_id'], ['id'], ondelete='SET NULL')
    
    # Drop indexes from contacts
    op.drop_index(op.f('ix_contacts_contact_list_id'), table_name='contacts')
    
    # Drop indexes from leads
    op.drop_index(op.f('ix_leads_assigned_to_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_lead_status'), table_name='leads')
    op.drop_index(op.f('ix_leads_contact_id'), table_name='leads')
    
    # Drop leads table
    op.drop_table('leads')
