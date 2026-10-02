from alembic import op
import sqlalchemy as sa
revision='0003'; down_revision='0002'

def upgrade():
    op.create_table('level_roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('guild_id', sa.BigInteger(), nullable=False, index=True),
        sa.Column('level', sa.Integer(), nullable=False, index=True),
        sa.Column('role_id', sa.BigInteger(), nullable=False, index=True),
        sa.UniqueConstraint('guild_id','level'),
        sa.UniqueConstraint('guild_id','role_id'))

def downgrade():
    op.drop_table('level_roles')
