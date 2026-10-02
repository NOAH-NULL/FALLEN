from alembic import op
import sqlalchemy as sa

revision = '0011_greeting_banner_data'
down_revision = '0010_warning_expiration'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('guild_configs', sa.Column('welcome_background_data', sa.LargeBinary(), nullable=True))
    op.add_column('guild_configs', sa.Column('goodbye_background_data', sa.LargeBinary(), nullable=True))


def downgrade():
    op.drop_column('guild_configs', 'goodbye_background_data')
    op.drop_column('guild_configs', 'welcome_background_data')