"""add contact list id to campaigns

Revision ID: 0005_add_contact_list_id
Revises: 00928737d7cf
Create Date: 2026-02-10 12:28:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005_add_contact_list_id'
down_revision = '00928737d7cf'
branch_labels = None
depends_on = None

def upgrade():
    # Add column if not exists (for safety on current DB where we manually added it)
    op.execute("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS contact_list_id UUID")
    
    # Drop constraint if exists before adding it to avoid naming conflicts/duplicates
    # op.drop_constraint doesn't have IF EXISTS in some SQLAlchemy versions, so we use raw SQL for safety
    op.execute("ALTER TABLE campaigns DROP CONSTRAINT IF EXISTS fk_campaigns_contact_list_id_contact_lists")
    
    # Add foreign key
    op.create_foreign_key(
        'fk_campaigns_contact_list_id_contact_lists',
        'campaigns', 'contact_lists',
        ['contact_list_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade():
    op.drop_constraint('fk_campaigns_contact_list_id_contact_lists', 'campaigns', type_='foreignkey')
    op.drop_column('campaigns', 'contact_list_id')
