from alembic import op
import sqlalchemy as sa
revision='0002';down_revision='0001'
def upgrade():
    op.add_column('guild_configs',sa.Column('log_channel_id',sa.BigInteger()))
    op.add_column('guild_configs',sa.Column('autorole_id',sa.BigInteger()))
    op.add_column('guild_configs',sa.Column('automod_enabled',sa.Boolean(),nullable=False,server_default=sa.text('false')))
    op.add_column('guild_configs',sa.Column('spam_limit',sa.Integer(),nullable=False,server_default='6'))
    op.add_column('guild_configs',sa.Column('spam_window',sa.Integer(),nullable=False,server_default='8'))
    op.create_table('warnings',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('guild_id',sa.BigInteger(),index=True),sa.Column('user_id',sa.BigInteger(),index=True),sa.Column('moderator_id',sa.BigInteger()),sa.Column('reason',sa.Text()),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now()))
    op.create_table('custom_commands',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('guild_id',sa.BigInteger(),index=True),sa.Column('name',sa.String(64)),sa.Column('response',sa.Text()),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now()),sa.UniqueConstraint('guild_id','name'))
    op.create_table('levels',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('guild_id',sa.BigInteger(),index=True),sa.Column('user_id',sa.BigInteger(),index=True),sa.Column('xp',sa.Integer(),nullable=False,server_default='0'),sa.Column('level',sa.Integer(),nullable=False,server_default='0'),sa.UniqueConstraint('guild_id','user_id'))
    op.create_table('reaction_roles',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('guild_id',sa.BigInteger(),index=True),sa.Column('message_id',sa.BigInteger(),index=True),sa.Column('emoji',sa.String(64)),sa.Column('role_id',sa.BigInteger()),sa.UniqueConstraint('guild_id','message_id','emoji'))
def downgrade():
    for t in ('reaction_roles','levels','custom_commands','warnings'):op.drop_table(t)
    for c in ('spam_window','spam_limit','automod_enabled','autorole_id','log_channel_id'):op.drop_column('guild_configs',c)
