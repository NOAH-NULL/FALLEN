"""persist member invite attribution

Revision ID: 0006_member_invite_attribution
Revises: 0005_invite_stats
"""
from alembic import op
import sqlalchemy as sa
revision='0006_member_invite_attribution'
down_revision='0005_invite_stats'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('member_invite_attribution',
        sa.Column('id',sa.Integer(),autoincrement=True,nullable=False),
        sa.Column('guild_id',sa.BigInteger(),nullable=False),
        sa.Column('member_id',sa.BigInteger(),nullable=False),
        sa.Column('inviter_id',sa.BigInteger(),nullable=False),
        sa.Column('invite_code',sa.String(length=128),nullable=True),
        sa.Column('joined_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column('left_at',sa.DateTime(timezone=True),nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('guild_id','member_id'),
    )
    op.create_index('ix_member_invite_attribution_guild_id','member_invite_attribution',['guild_id'])
    op.create_index('ix_member_invite_attribution_member_id','member_invite_attribution',['member_id'])
    op.create_index('ix_member_invite_attribution_inviter_id','member_invite_attribution',['inviter_id'])

def downgrade():
    op.drop_index('ix_member_invite_attribution_inviter_id',table_name='member_invite_attribution')
    op.drop_index('ix_member_invite_attribution_member_id',table_name='member_invite_attribution')
    op.drop_index('ix_member_invite_attribution_guild_id',table_name='member_invite_attribution')
    op.drop_table('member_invite_attribution')
