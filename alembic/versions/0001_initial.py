from alembic import op
import sqlalchemy as sa
revision='0001'; down_revision=None

def upgrade():
    op.create_table('guild_configs',sa.Column('guild_id',sa.BigInteger(),primary_key=True),sa.Column('welcome_channel_id',sa.BigInteger()),sa.Column('goodbye_channel_id',sa.BigInteger()),sa.Column('welcome_message',sa.Text(),nullable=False),sa.Column('goodbye_message',sa.Text(),nullable=False),sa.Column('welcome_background',sa.Text(),nullable=False),sa.Column('goodbye_background',sa.Text(),nullable=False))
def downgrade(): op.drop_table('guild_configs')
