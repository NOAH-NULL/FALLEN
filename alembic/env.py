from __future__ import annotations
import asyncio, os
from dotenv import load_dotenv
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from bot.models import Base

load_dotenv()
config=context.config
url=os.getenv('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
if not url: raise RuntimeError('DATABASE_URL is required for Alembic')
config.set_main_option('sqlalchemy.url', url.replace('%','%%'))
target_metadata=Base.metadata

def run_migrations_offline():
    context.configure(url=url,target_metadata=target_metadata,literal_binds=True,dialect_opts={'paramstyle':'named'},compare_type=True,compare_server_default=True)
    with context.begin_transaction(): context.run_migrations()

async def run_async_migrations():
    connectable=async_engine_from_config(config.get_section(config.config_ini_section, {}), prefix='sqlalchemy.', poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(lambda conn: context.configure(connection=conn,target_metadata=target_metadata,compare_type=True,compare_server_default=True))
        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()

def run_migrations_online(): asyncio.run(run_async_migrations())

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
