"""Add durable V16 capability tables."""
from alembic import op
import sqlalchemy as sa
revision = "0009_v16_capabilities"
down_revision = "0008_extreme_settings"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('feature_records',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False),
        sa.Column('subject_id', sa.BigInteger(), nullable=True), sa.Column('feature', sa.String(64), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('guild_id','subject_id','feature'))
    op.create_table('security_events',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False),
        sa.Column('actor_id', sa.BigInteger(), nullable=True), sa.Column('target_id', sa.BigInteger(), nullable=True),
        sa.Column('event_type', sa.String(64), nullable=False), sa.Column('details', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('scheduled_actions',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False),
        sa.Column('target_id', sa.BigInteger(), nullable=False), sa.Column('action', sa.String(32), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column('run_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('executed', sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('automod_rules',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False), sa.Column('name', sa.String(64), nullable=False),
        sa.Column('kind', sa.String(32), nullable=False), sa.Column('pattern', sa.Text(), nullable=False, server_default=''), sa.Column('action', sa.String(32), nullable=False, server_default='delete'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column('config', sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.UniqueConstraint('guild_id','name'))
    op.create_table('member_profiles',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False), sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('bio', sa.Text(), nullable=False, server_default=''), sa.Column('color', sa.Integer(), nullable=True), sa.Column('badges', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('birthday', sa.String(10), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint('guild_id','user_id'))
    op.create_table('reputation',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False), sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'), sa.UniqueConstraint('guild_id','user_id'))
    op.create_table('playlists',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False), sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(64), nullable=False), sa.Column('tracks', sa.JSON(), nullable=False, server_default='[]'), sa.Column('server_wide', sa.Boolean(), nullable=False, server_default=sa.false()), sa.UniqueConstraint('guild_id','owner_id','name'))
    op.create_table('tickets_v16',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False), sa.Column('channel_id', sa.BigInteger(), nullable=False, unique=True),
        sa.Column('opener_id', sa.BigInteger(), nullable=False), sa.Column('claimer_id', sa.BigInteger(), nullable=True), sa.Column('category', sa.String(64), nullable=False, server_default='general'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'), sa.Column('status', sa.String(16), nullable=False, server_default='open'), sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('rating', sa.Integer(), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table('config_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('guild_id', sa.BigInteger(), nullable=False), sa.Column('created_by', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(64), nullable=False), sa.Column('payload', sa.JSON(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint('guild_id','name'))
    for table, cols in {
        'feature_records':['guild_id','subject_id','feature'], 'security_events':['guild_id','actor_id','target_id','event_type'],
        'scheduled_actions':['guild_id','target_id','action','run_at'], 'automod_rules':['guild_id','kind'], 'member_profiles':['guild_id','user_id'],
        'reputation':['guild_id','user_id'], 'playlists':['guild_id','owner_id'], 'tickets_v16':['guild_id','opener_id','status'], 'config_snapshots':['guild_id']}.items():
        for c in cols:
            op.create_index(f'ix_{table}_{c}', table, [c], unique=False)

def downgrade():
    for t in ['config_snapshots','tickets_v16','playlists','reputation','member_profiles','automod_rules','scheduled_actions','security_events','feature_records']:
        op.drop_table(t)
