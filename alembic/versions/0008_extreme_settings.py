"""Add persistent V16 extreme feature configuration."""
from alembic import op
import sqlalchemy as sa
revision="0008_extreme_settings"
down_revision="0007_runtime_schema"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("guild_configs", sa.Column("extreme_settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
def downgrade():
    op.drop_column("guild_configs", "extreme_settings")
