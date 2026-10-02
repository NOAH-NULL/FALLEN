"""invite tracking stats

Revision ID: 0005_invite_stats
Revises: 0004_greeting_embeds
"""
from alembic import op
import sqlalchemy as sa

revision = '0005_invite_stats'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'invite_stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('guild_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('joins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('leaves', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('guild_id', 'user_id'),
    )
    op.create_index('ix_invite_stats_guild_id', 'invite_stats', ['guild_id'])
    op.create_index('ix_invite_stats_user_id', 'invite_stats', ['user_id'])

def downgrade():
    op.drop_index('ix_invite_stats_user_id', table_name='invite_stats')
    op.drop_index('ix_invite_stats_guild_id', table_name='invite_stats')
    op.drop_table('invite_stats')
