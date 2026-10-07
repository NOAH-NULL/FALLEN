from alembic import op
import sqlalchemy as sa

revision = "0017_welcome_engine"
down_revision = "0016_greeting_advanced"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "guild_configs",
        sa.Column(
            "welcome_settings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.alter_column("guild_configs", "welcome_settings", server_default=None)


def downgrade():
    op.drop_column("guild_configs", "welcome_settings")
