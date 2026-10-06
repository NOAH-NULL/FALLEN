from alembic import op
import sqlalchemy as sa

revision = "0013_leveling_v2"
down_revision = "0012_scheduler_claims"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("levels", sa.Column("total_xp", sa.BigInteger(), nullable=False, server_default="0"))
    op.create_table(
        "level_settings",
        sa.Column("guild_id", sa.BigInteger(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("xp_min", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("xp_max", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("announce", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("announcement_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("no_xp_roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("no_xp_channels", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("bonus_roles", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.alter_column("levels", "total_xp", server_default=None)

def downgrade():
    op.drop_table("level_settings")
    op.drop_column("levels", "total_xp")
