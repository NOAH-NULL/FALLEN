from alembic import op
import sqlalchemy as sa

revision = "0015_leveling_message_xp"
down_revision = "0014_leveling_stack_awards"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "level_settings",
        sa.Column("message_xp_mode", sa.String(length=24), nullable=False, server_default="per_character"),
    )
    op.add_column(
        "level_settings",
        sa.Column("xp_per_character", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "level_settings",
        sa.Column("max_character_xp", sa.Integer(), nullable=False, server_default="75"),
    )
    op.add_column(
        "level_settings",
        sa.Column("xp_channels", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.alter_column("level_settings", "message_xp_mode", server_default=None)
    op.alter_column("level_settings", "xp_per_character", server_default=None)
    op.alter_column("level_settings", "max_character_xp", server_default=None)
    op.alter_column("level_settings", "xp_channels", server_default=None)


def downgrade():
    op.drop_column("level_settings", "xp_channels")
    op.drop_column("level_settings", "max_character_xp")
    op.drop_column("level_settings", "xp_per_character")
    op.drop_column("level_settings", "message_xp_mode")
