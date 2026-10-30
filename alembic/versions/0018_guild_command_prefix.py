from alembic import op
import sqlalchemy as sa

revision = "0018_guild_command_prefix"
down_revision = "0017_welcome_engine"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "guild_configs",
        sa.Column("command_prefix", sa.String(length=5), nullable=False, server_default=","),
    )
    op.alter_column("guild_configs", "command_prefix", server_default=None)


def downgrade():
    op.drop_column("guild_configs", "command_prefix")
