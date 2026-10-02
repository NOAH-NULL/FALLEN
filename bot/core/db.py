from contextlib import asynccontextmanager
from time import perf_counter
from collections.abc import Awaitable, Callable
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from bot.core.fencing import current_fence, StaleLeaseError
from bot.core.metrics import DB_LATENCY


class FencedAsyncSession(AsyncSession):
    async def commit(self):
        guard = getattr(self, "_fence_guard", None)
        ctx = current_fence()
        if guard is not None and ctx is not None:
            if not await guard(ctx.shard_id, ctx.fence):
                await self.rollback()
                raise StaleLeaseError(
                    f"stale shard fence rejected before commit shard={ctx.shard_id} fence={ctx.fence}"
                )
        return await super().commit()


class Database:
    def __init__(self, settings):
        connect_args={'command_timeout':settings.db_statement_timeout_ms/1000}
        if settings.db_use_pgbouncer:
            connect_args.update({'statement_cache_size': 0, 'prepared_statement_cache_size': 0})
        self.engine=create_async_engine(
            settings.database_url, pool_pre_ping=True, pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow, pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle, connect_args=connect_args,
        )
        self.sessions=async_sessionmaker(self.engine, expire_on_commit=False, class_=FencedAsyncSession)
        self._fence_guard: Callable[[int, int], Awaitable[bool]] | None = None

    def set_fence_guard(self, guard):
        self._fence_guard = guard

    @asynccontextmanager
    async def session(self):
        started=perf_counter()
        try:
            async with self.sessions() as session:
                session._fence_guard = self._fence_guard
                yield session
        finally: DB_LATENCY.labels('session').observe(perf_counter()-started)

    async def health(self):
        async with self.engine.connect() as conn: await conn.execute(text('SELECT 1'))
        return True
    async def close(self): await self.engine.dispose()
