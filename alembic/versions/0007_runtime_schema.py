"""complete runtime schema for V15 features

Revision ID: 0007_runtime_schema
Revises: 0006_member_invite_attribution
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_runtime_schema"
down_revision = "0006_member_invite_attribution"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("guild_configs", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("guild_configs", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    op.create_table("mod_cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default="No reason provided"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mod_cases_guild_id", "mod_cases", ["guild_id"])
    op.create_index("ix_mod_cases_target_id", "mod_cases", ["target_id"])
    op.create_index("ix_mod_cases_moderator_id", "mod_cases", ["moderator_id"])
    op.create_index("ix_mod_cases_action", "mod_cases", ["action"])

    op.create_table("reminders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_reminders_guild_id", "reminders", ["guild_id"])
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_index("ix_reminders_due_at", "reminders", ["due_at"])
    op.create_index("ix_reminders_delivered", "reminders", ["delivered"])

    op.create_table("giveaways",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("prize", sa.String(200), nullable=False),
        sa.Column("winner_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_giveaways_guild_id", "giveaways", ["guild_id"])
    op.create_index("ix_giveaways_channel_id", "giveaways", ["channel_id"])
    op.create_index("ix_giveaways_ends_at", "giveaways", ["ends_at"])
    op.create_index("ix_giveaways_ended", "giveaways", ["ended"])

    op.create_table("suggestions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_suggestions_guild_id", "suggestions", ["guild_id"])
    op.create_index("ix_suggestions_user_id", "suggestions", ["user_id"])
    op.create_index("ix_suggestions_channel_id", "suggestions", ["channel_id"])
    op.create_index("ix_suggestions_status", "suggestions", ["status"])

    op.create_table("role_menus",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("emoji", sa.String(64), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("guild_id", "message_id", "emoji"),
    )
    op.create_index("ix_role_menus_guild_id", "role_menus", ["guild_id"])
    op.create_index("ix_role_menus_message_id", "role_menus", ["message_id"])

    op.create_table("economy",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("guild_id", "user_id"),
    )
    op.create_index("ix_economy_guild_id", "economy", ["guild_id"])
    op.create_index("ix_economy_user_id", "economy", ["user_id"])

def downgrade():
    for name in ("ix_economy_user_id", "ix_economy_guild_id"):
        op.drop_index(name, table_name="economy")
    op.drop_table("economy")
    op.drop_index("ix_role_menus_message_id", table_name="role_menus")
    op.drop_index("ix_role_menus_guild_id", table_name="role_menus")
    op.drop_table("role_menus")
    for name in ("ix_suggestions_status", "ix_suggestions_channel_id", "ix_suggestions_user_id", "ix_suggestions_guild_id"):
        op.drop_index(name, table_name="suggestions")
    op.drop_table("suggestions")
    for name in ("ix_giveaways_ended", "ix_giveaways_ends_at", "ix_giveaways_channel_id", "ix_giveaways_guild_id"):
        op.drop_index(name, table_name="giveaways")
    op.drop_table("giveaways")
    for name in ("ix_reminders_delivered", "ix_reminders_due_at", "ix_reminders_user_id", "ix_reminders_guild_id"):
        op.drop_index(name, table_name="reminders")
    op.drop_table("reminders")
    for name in ("ix_mod_cases_action", "ix_mod_cases_moderator_id", "ix_mod_cases_target_id", "ix_mod_cases_guild_id"):
        op.drop_index(name, table_name="mod_cases")
    op.drop_table("mod_cases")
    op.drop_column("guild_configs", "updated_at")
    op.drop_column("guild_configs", "created_at")
