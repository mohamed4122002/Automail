"""update email variant

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003_comprehensive_sync'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop columns from the old "Test Container" model
    op.drop_column('email_variants', 'subject_a')
    op.drop_column('email_variants', 'subject_b')
    op.drop_column('email_variants', 'winner')
    op.drop_column('email_variants', 'status')
    op.drop_column('email_variants', 'test_limit')
    op.drop_column('email_variants', 'total_sent')
    
    # Add columns for the new "Single Variant" model
    op.add_column('email_variants', sa.Column('subject', sa.String(length=255), nullable=True))
    op.add_column('email_variants', sa.Column('html_body', sa.Text(), nullable=True))
    op.add_column('email_variants', sa.Column('weight', sa.Float(), nullable=True))
    
    # Update existing rows to have default values if needed, then make nullable=False
    op.execute("UPDATE email_variants SET weight = 0.5 WHERE weight IS NULL")
    op.execute("UPDATE email_variants SET subject = 'Legacy Variant' WHERE subject IS NULL")
    op.execute("UPDATE email_variants SET html_body = '<p></p>' WHERE html_body IS NULL")
    
    # Now set nullable=False matches models.py
    op.alter_column('email_variants', 'subject', nullable=False)
    op.alter_column('email_variants', 'html_body', nullable=False)
    # weight has a default in model but strictly in DB it should be non-null if model says Mapped[float]
    op.alter_column('email_variants', 'weight', nullable=False)


def downgrade() -> None:
    # Reverse the changes
    op.add_column('email_variants', sa.Column('test_limit', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('email_variants', sa.Column('status', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.add_column('email_variants', sa.Column('winner', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.add_column('email_variants', sa.Column('subject_b', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('email_variants', sa.Column('subject_a', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('email_variants', sa.Column('total_sent', sa.INTEGER(), server_default='0', autoincrement=False, nullable=False))
    
    op.drop_column('email_variants', 'weight')
    op.drop_column('email_variants', 'html_body')
    op.drop_column('email_variants', 'subject')
