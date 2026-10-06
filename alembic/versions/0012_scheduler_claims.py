from alembic import op
import sqlalchemy as sa

revision = '0012_scheduler_claims'
down_revision = '0011_greeting_banner_data'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scheduled_actions', sa.Column('processing', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('scheduled_actions', sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_scheduled_actions_processing', 'scheduled_actions', ['processing'])
    op.create_index('ix_scheduled_actions_claimed_at', 'scheduled_actions', ['claimed_at'])

    op.add_column('reminders', sa.Column('processing', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('reminders', sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_reminders_processing', 'reminders', ['processing'])
    op.create_index('ix_reminders_claimed_at', 'reminders', ['claimed_at'])


def downgrade():
    op.drop_index('ix_reminders_claimed_at', table_name='reminders')
    op.drop_index('ix_reminders_processing', table_name='reminders')
    op.drop_column('reminders', 'claimed_at')
    op.drop_column('reminders', 'processing')

    op.drop_index('ix_scheduled_actions_claimed_at', table_name='scheduled_actions')
    op.drop_index('ix_scheduled_actions_processing', table_name='scheduled_actions')
    op.drop_column('scheduled_actions', 'claimed_at')
    op.drop_column('scheduled_actions', 'processing')
