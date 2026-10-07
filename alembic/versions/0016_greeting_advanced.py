from alembic import op
import sqlalchemy as sa


revision = "0016_greeting_advanced"
down_revision = "0015_leveling_message_xp"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "guild_configs",
        sa.Column("welcome_dm_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "guild_configs",
        sa.Column(
            "welcome_dm_message",
            sa.Text(),
            nullable=False,
            server_default="Welcome to {server}, {name}! We are glad to have you here.",
        ),
    )
    op.add_column(
        "guild_configs",
        sa.Column("welcome_button_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "guild_configs",
        sa.Column("welcome_button_label", sa.String(length=80), nullable=False, server_default="Read the Rules"),
    )
    op.add_column(
        "guild_configs",
        sa.Column("welcome_button_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "guild_configs",
        sa.Column("welcome_show_details", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.alter_column("guild_configs", "welcome_dm_enabled", server_default=None)
    op.alter_column("guild_configs", "welcome_dm_message", server_default=None)
    op.alter_column("guild_configs", "welcome_button_enabled", server_default=None)
    op.alter_column("guild_configs", "welcome_button_label", server_default=None)
    op.alter_column("guild_configs", "welcome_show_details", server_default=None)


def downgrade():
    op.drop_column("guild_configs", "welcome_show_details")
    op.drop_column("guild_configs", "welcome_button_url")
    op.drop_column("guild_configs", "welcome_button_label")
    op.drop_column("guild_configs", "welcome_button_enabled")
    op.drop_column("guild_configs", "welcome_dm_message")
    op.drop_column("guild_configs", "welcome_dm_enabled")
