from alembic import op
import sqlalchemy as sa

revision="0004"
down_revision="0003"

def upgrade():
    op.add_column("guild_configs", sa.Column("welcome_embed_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("guild_configs", sa.Column("goodbye_embed_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("guild_configs", sa.Column("welcome_embed_title", sa.Text(), nullable=False, server_default="Welcome!"))
    op.add_column("guild_configs", sa.Column("goodbye_embed_title", sa.Text(), nullable=False, server_default="Goodbye!"))
    op.add_column("guild_configs", sa.Column("welcome_embed_description", sa.Text(), nullable=False, server_default="{mention} just joined {server}! 🎉"))
    op.add_column("guild_configs", sa.Column("goodbye_embed_description", sa.Text(), nullable=False, server_default="{name} has left {server}. 👋"))
    op.add_column("guild_configs", sa.Column("welcome_embed_color", sa.BigInteger(), nullable=False, server_default="5793266"))
    op.add_column("guild_configs", sa.Column("goodbye_embed_color", sa.BigInteger(), nullable=False, server_default="9807270"))

def downgrade():
    for c in ("goodbye_embed_color","welcome_embed_color","goodbye_embed_description","welcome_embed_description","goodbye_embed_title","welcome_embed_title","goodbye_embed_enabled","welcome_embed_enabled"):
        op.drop_column("guild_configs", c)
