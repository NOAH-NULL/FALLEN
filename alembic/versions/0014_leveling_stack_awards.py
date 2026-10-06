from alembic import op
import sqlalchemy as sa

revision = "0014_leveling_stack_awards"
down_revision = "0013_leveling_v2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "level_settings",
        sa.Column("stack_awards", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    # 0013 created total_xp with a zero default. Preserve existing leveling progress
    # from the pre-total-XP schema by reconstructing it from the old 100*(level+1)
    # progression. New rows remain untouched.
    op.execute(
        """
        UPDATE levels
        SET total_xp = (level * (level + 1) / 2) * 100 + xp
        WHERE total_xp = 0 AND (level > 0 OR xp > 0)
        """
    )
    op.alter_column("level_settings", "stack_awards", server_default=None)


def downgrade():
    op.drop_column("level_settings", "stack_awards")
