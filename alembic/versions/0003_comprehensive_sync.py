"""comprehensive schema sync

Revision ID: 0003_comprehensive_sync
Revises: 0002_condition_logs
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003_comprehensive_sync'
down_revision = '0002_condition_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create LeadStatusEnum type
    lead_status_enum = postgresql.ENUM('hot', 'warm', 'cold', 'new', 'unsubscribed', name='leadstatusenum')
    lead_status_enum.create(op.get_bind())

    # 2. Add columns to users table
    op.add_column('users', sa.Column('lead_status', sa.Enum('hot', 'warm', 'cold', 'new', 'unsubscribed', name='leadstatusenum'), nullable=False, server_default='new'))
    op.add_column('users', sa.Column('claimed_by_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('claimed_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_users_lead_status'), 'users', ['lead_status'], unique=False)
    op.create_foreign_key('fk_users_claimed_by', 'users', 'users', ['claimed_by_id'], ['id',], ondelete='SET NULL')

    # 3. Add columns to campaigns table
    op.add_column('campaigns', sa.Column('retry_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{"enabled": true, "first_retry_hours": 48, "second_retry_hours": 72, "max_attempts": 3}', nullable=False))
    op.add_column('campaigns', sa.Column('warmup_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{"enabled": false, "initial_volume": 10, "daily_increase_pct": 10.0, "max_volume": 1000, "current_limit": 10}', nullable=False))
    op.add_column('campaigns', sa.Column('warmup_last_limit_increase', sa.DateTime(), nullable=True))
    op.add_column('campaigns', sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_campaigns_owner', 'campaigns', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_campaigns_owner_id'), 'campaigns', ['owner_id'], unique=False)

    # 4. Add columns to email_sends table
    op.add_column('email_sends', sa.Column('unsubscribe_token', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')))
    op.add_column('email_sends', sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('email_sends', sa.Column('variant_letter', sa.String(length=1), nullable=True))
    op.create_unique_constraint('uq_email_sends_unsubscribe_token', 'email_sends', ['unsubscribe_token'])
    op.create_index(op.f('ix_email_sends_unsubscribe_token'), 'email_sends', ['unsubscribe_token'], unique=True)

    # 5. Create new tables
    op.create_table('workflow_instance_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['instance_id'], ['workflow_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id')
    )

    op.create_table('workflow_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('data_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('condition_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['instance_id'], ['workflow_instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_id'], ['workflow_nodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['step_id'], ['workflow_steps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_snapshots_instance_id'), 'workflow_snapshots', ['instance_id'], unique=False)
    op.create_index(op.f('ix_workflow_snapshots_step_id'), 'workflow_snapshots', ['step_id'], unique=False)

    op.create_table('email_variants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('workflow_step_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject_a', sa.String(length=255), nullable=False),
        sa.Column('subject_b', sa.String(length=255), nullable=False),
        sa.Column('winner', sa.String(length=1), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('total_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('test_limit', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_step_id'], ['workflow_steps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('email_sending_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('html_body', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('scheduled_for', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('user_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_notes_user_id'), 'user_notes', ['user_id'], unique=False)

    op.create_table('contact_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contact_lists_owner_id'), 'contact_lists', ['owner_id'], unique=False)

    op.create_table('contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['contact_list_id'], ['contact_lists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contacts_contact_list_id'), 'contacts', ['contact_list_id'], unique=False)
    op.create_index(op.f('ix_contacts_email'), 'contacts', ['email'], unique=False)

    op.create_table('email_retry_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_send_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['email_send_id'], ['email_sends.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_retry_attempts_campaign_id'), 'email_retry_attempts', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_email_retry_attempts_email_send_id'), 'email_retry_attempts', ['email_send_id'], unique=False)
    op.create_index(op.f('ix_email_retry_attempts_user_id'), 'email_retry_attempts', ['user_id'], unique=False)

    op.create_table('settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=True)

    # 6. Add foreign key to email_sends (variant_id)
    op.create_foreign_key('fk_email_sends_variant', 'email_sends', 'email_variants', ['variant_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_email_sends_variant', 'email_sends', type_='foreignkey')
    op.drop_index(op.f('ix_settings_key'), table_name='settings')
    op.drop_table('settings')
    op.drop_index(op.f('ix_email_retry_attempts_user_id'), table_name='email_retry_attempts')
    op.drop_index(op.f('ix_email_retry_attempts_email_send_id'), table_name='email_retry_attempts')
    op.drop_index(op.f('ix_email_retry_attempts_campaign_id'), table_name='email_retry_attempts')
    op.drop_table('email_retry_attempts')
    op.drop_index(op.f('ix_contacts_email'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_contact_list_id'), table_name='contacts')
    op.drop_table('contacts')
    op.drop_index(op.f('ix_contact_lists_owner_id'), table_name='contact_lists')
    op.drop_table('contact_lists')
    op.drop_index(op.f('ix_user_notes_user_id'), table_name='user_notes')
    op.drop_table('user_notes')
    op.drop_table('email_sending_queue')
    op.drop_table('email_variants')
    op.drop_index(op.f('ix_workflow_snapshots_step_id'), table_name='workflow_snapshots')
    op.drop_index(op.f('ix_workflow_snapshots_instance_id'), table_name='workflow_snapshots')
    op.drop_table('workflow_snapshots')
    op.drop_table('workflow_instance_data')
    
    op.drop_index(op.f('ix_email_sends_unsubscribe_token'), table_name='email_sends')
    op.drop_constraint('uq_email_sends_unsubscribe_token', 'email_sends', type_='unique')
    op.drop_column('email_sends', 'variant_letter')
    op.drop_column('email_sends', 'variant_id')
    op.drop_column('email_sends', 'unsubscribe_token')
    
    op.drop_index(op.f('ix_campaigns_owner_id'), table_name='campaigns')
    op.drop_constraint('fk_campaigns_owner', 'campaigns', type_='foreignkey')
    op.drop_column('campaigns', 'owner_id')
    op.drop_column('campaigns', 'warmup_last_limit_increase')
    op.drop_column('campaigns', 'warmup_config')
    op.drop_column('campaigns', 'retry_config')
    
    op.drop_constraint('fk_users_claimed_by', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_lead_status'), table_name='users')
    op.drop_column('users', 'claimed_at')
    op.drop_column('users', 'claimed_by_id')
    op.drop_column('users', 'lead_status')
    
    # Drop leadstatusenum type
    sa.Enum(name='leadstatusenum').drop(op.get_bind())
